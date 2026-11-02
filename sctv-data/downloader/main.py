"""Resumable SCTV EPG downloader. Configure the endpoint adapter before use."""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import anyio
import httpx


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def atomic_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".notfinished")
    with tmp.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, separators=(",", ":"))
        fp.flush()
        os.fsync(fp.fileno())
    os.replace(tmp, path)


def dates_inclusive(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


@dataclass(frozen=True)
class Settings:
    channel_ids: list[int] | str
    dates: tuple[date, ...]
    targets: tuple[dict[str, str], ...]
    root: Path
    concurrency: int
    timeout: float
    retry_seconds: float
    backoff: float
    max_attempts: int
    reporting_interval: float

    @classmethod
    def load(cls, filename: Path) -> Settings:
        with filename.open("rb") as fp:
            raw = tomllib.load(fp)
        ids = raw["channels"]["ids"]
        if ids != "*" and (
            not isinstance(ids, list)
            or not ids
            or any(type(x) is not int or x < 0 for x in ids)
        ):
            raise ValueError(
                'channels.ids must be "*" or a nonempty list of nonnegative integers'
            )
        rng = raw["range"]
        if "targets" in rng and ("from" in rng or "to" in rng):
            raise ValueError("Use range.targets OR range.from/to, not both")
        raw_targets = rng.get("targets")
        if raw_targets is None:
            raw_targets = [{"from": rng["from"], "to": rng["to"]}]
        if not isinstance(raw_targets, list) or not raw_targets:
            raise ValueError("range.targets must be a nonempty array")
        all_days: set[date] = set()
        targets = []

        def parse_day(value):
            if isinstance(value, datetime):
                raise ValueError("Use dates, not datetimes")
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                return date.fromisoformat(value)
            raise ValueError(f"Invalid date: {value!r}")

        for item in raw_targets:
            if not isinstance(item, dict):
                raise ValueError("Each target must be a TOML inline table")
            if set(item) == {"date"}:
                start = end = parse_day(item["date"])
                targets.append({"date": start.isoformat()})
            elif set(item) == {"from", "to"}:
                start, end = parse_day(item["from"]), parse_day(item["to"])
                targets.append({"from": start.isoformat(), "to": end.isoformat()})
            else:
                raise ValueError("Each target needs date OR both from and to")
            if start > end:
                raise ValueError(f"Reversed target: {item}")
            all_days.update(dates_inclusive(start, end))
        cfg = raw["downloader"]
        result = cls(
            ids,
            tuple(sorted(all_days)),
            tuple(targets),
            Path(raw["output"]["directory"]),
            int(cfg["max-concurrent-requests"]),
            float(cfg["timeout"]),
            float(cfg["retry"]) / 1000,
            float(cfg["backoff"]),
            int(cfg.get("max-attempts", 5)),
            float(cfg.get("reporting-interval", 10)),
        )
        if (
            result.concurrency < 1
            or result.timeout <= 0
            or result.retry_seconds < 0
            or result.backoff < 1
            or result.max_attempts < 1
        ):
            raise ValueError("Invalid downloader settings")
        return result


class SCTVAdapter:
    """Replace the methods below with the actual SCTV API request contract."""

    async def discover_channels(self, client: httpx.AsyncClient) -> list[int]:
        raise NotImplementedError(
            "Implement SCTV channel discovery or use explicit channel IDs"
        )

    async def fetch(self, client: httpx.AsyncClient, channel_id: int, day: date) -> Any:
        # Example once the real API contract is known:
        # response = await client.post(URL, json={"channel": channel_id, "date": day.isoformat()})
        # response.raise_for_status()
        # return response.json()
        raise NotImplementedError(
            "Implement SCTVAdapter.fetch with the real API URL and payload"
        )


class Downloader:
    def __init__(self, settings: Settings, adapter: SCTVAdapter):
        self.cfg = settings
        self.adapter = adapter
        self.lock = anyio.Lock()
        self.stats = {
            "total": 0,
            "completed": 0,
            "skipped": 0,
            "failed": 0,
            "pending": 0,
        }
        self.errors: list[dict[str, Any]] = []
        self.started = timestamp()
        self.channels: list[int] = []
        self.state = "running"

    def target(self, channel: int, day: date) -> Path:
        return (
            self.cfg.root
            / "data"
            / str(channel)
            / day.strftime("%Y-%m")
            / f"{day:%d}.json"
        )

    async def snapshot(self):
        async with self.lock:
            self.stats["pending"] = (
                self.stats["total"]
                - self.stats["completed"]
                - self.stats["skipped"]
                - self.stats["failed"]
            )
            status = {
                "schema_version": 1,
                "state": self.state,
                "range": {"targets": list(self.cfg.targets)},
                "channels": {
                    "requested": self.cfg.channel_ids,
                    "discovered": len(self.channels),
                },
                "progress": dict(self.stats),
                "started_at": self.started,
                "updated_at": timestamp(),
                "finished_at": timestamp() if self.state != "running" else None,
                "recent_errors": self.errors[-30:],
            }
            await anyio.to_thread.run_sync(
                atomic_json, self.cfg.root / "status.json", status
            )

    async def one(self, client: httpx.AsyncClient, channel: int, day: date):
        dest = self.target(channel, day)
        if dest.is_file():
            async with self.lock:
                self.stats["skipped"] += 1
            return
        error = None
        for attempt in range(self.cfg.max_attempts):
            try:
                data = await self.adapter.fetch(client, channel, day)
                # JSON encoding happens before the file is atomically committed.
                await anyio.to_thread.run_sync(atomic_json, dest, data)
                async with self.lock:
                    self.stats["completed"] += 1
                return
            except (httpx.HTTPError, ValueError, OSError) as exc:
                error = str(exc)
                if isinstance(exc, httpx.HTTPStatusError):
                    code = exc.response.status_code
                    if code not in (408, 429) and code < 500:
                        break
                if attempt + 1 < self.cfg.max_attempts:
                    await anyio.sleep(
                        self.cfg.retry_seconds * self.cfg.backoff**attempt
                    )
        async with self.lock:
            self.stats["failed"] += 1
            self.errors.append(
                {"channel": channel, "date": day.isoformat(), "error": error}
            )

    async def run(self):
        self.cfg.root.mkdir(parents=True, exist_ok=True)
        limits = httpx.Limits(
            max_connections=self.cfg.concurrency,
            max_keepalive_connections=self.cfg.concurrency,
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.cfg.timeout, limits=limits, follow_redirects=False
            ) as client:
                self.channels = (
                    await self.adapter.discover_channels(client)
                    if self.cfg.channel_ids == "*"
                    else sorted(set(self.cfg.channel_ids))
                )
                days = len(self.cfg.dates)
                self.stats["total"] = len(self.channels) * days
                await self.snapshot()
                send, receive = anyio.create_memory_object_stream[tuple[int, date]](
                    self.cfg.concurrency * 2
                )

                async def producer():
                    async with send:
                        # Interleave channels globally: each date schedules all
                        # channels before advancing to the next date.
                        for day in self.cfg.dates:
                            for channel in self.channels:
                                await send.send((channel, day))

                async def worker():
                    async with receive.clone() as incoming:
                        async for channel, day in incoming:
                            await self.one(client, channel, day)

                async def reporter():
                    while True:
                        await anyio.sleep(self.cfg.reporting_interval)
                        await self.snapshot()
                        p = self.stats
                        print(
                            f"completed={p['completed']} skipped={p['skipped']} failed={p['failed']} / {p['total']}",
                            flush=True,
                        )

                async with anyio.create_task_group() as group:
                    group.start_soon(reporter)
                    async with anyio.create_task_group() as jobs:
                        jobs.start_soon(producer)
                        for _ in range(self.cfg.concurrency):
                            jobs.start_soon(worker)
                    group.cancel_scope.cancel()
            self.state = (
                "finished" if not self.stats["failed"] else "finished_with_errors"
            )
        except BaseException:
            self.state = "interrupted"
            with anyio.CancelScope(shield=True):
                await self.snapshot()
            raise
        await self.snapshot()
