#!/usr/bin/env python3
"""Resumable VTVgo EPG collector: niquests + AnyIO + uvloop.

Data is stored as original API-response JSON, one file per channel batch and
inclusive date range. No network calls are made until you run this script.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import anyio
import niquests

URL = "https://api.vtvdigital.org/display/v21.0/epg"
MAX_CHANNELS = 20
MAX_CELLS = 120
LOG = logging.getLogger("vtvgo")
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class Job:
    group: int
    ids: tuple[str, ...]
    first: date
    last: date

    @property
    def key(self) -> str:
        return f"group_{self.group:02d}/{self.first}_{self.last}.json"

    def metadata(self) -> dict:
        return {"channelIDs": list(self.ids), "from": self.first.isoformat(),
                "to": self.last.isoformat()}


def catalog_channels(path: Path) -> list[str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    ids = dict.fromkeys(
        str(ch["id"])
        for group in obj["data"]
        for ch in group.get("channels", [])
        if ch.get("enabled", True) and ch.get("epgChannelId")
    )
    return list(ids)


def make_jobs(ids: list[str], first: date, last: date):
    for group, offset in enumerate(range(0, len(ids), MAX_CHANNELS), start=1):
        batch = tuple(ids[offset:offset + MAX_CHANNELS])
        max_days = MAX_CELLS // len(batch)
        day = first
        while day <= last:
            finish = min(day + timedelta(days=max_days - 1), last)
            assert len(batch) <= MAX_CHANNELS
            assert len(batch) * ((finish - day).days + 1) <= MAX_CELLS
            yield Job(group, batch, day, finish)
            day = finish + timedelta(days=1)


def existing_valid(path: Path, job: Job) -> bool:
    if not path.is_file():
        return False
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return (isinstance(obj, dict) and isinstance(obj.get("data"), dict)
                and obj.get("_request") == job.metadata())
    except (OSError, ValueError, TypeError):
        return False


def validate_payload(obj: object, job: Job) -> dict:
    if not isinstance(obj, dict) or not isinstance(obj.get("data"), dict):
        raise ValueError("Response did not have a data object")
    for channel_id, days in obj["data"].items():
        if channel_id not in job.ids:
            raise ValueError(f"Unexpected channel ID {channel_id!r}")
        if not isinstance(days, list):
            raise ValueError(f"Expected list for channel {channel_id}")
        for record in days:
            if not isinstance(record, dict):
                raise ValueError("Non-object date record")
            dt = date.fromisoformat(record["date"])
            if not job.first <= dt <= job.last:
                raise ValueError(f"Out of-range date {dt} in response")
            if not isinstance(record.get("programs"), list):
                raise ValueError(f"Missing programs list for {channel_id}/{dt}")
    return obj


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    try:
        with tmp.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def retry_wait(value: str | None, attempt: int) -> float:
    if value:
        try:
            return max(0, min(120, float(value)))
        except ValueError:
            try:
                target = parsedate_to_datetime(value)
                return max(0, min(120, (target - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                pass
    return min(30, 2 ** attempt) + random.uniform(0, 0.5)


async def fetch(session: niquests.AsyncSession, job: Job, retries: int) -> dict:
    params = {"channelIDs": ",".join(job.ids),
              "from": job.first.isoformat(), "to": job.last.isoformat()}
    for attempt in range(1, retries + 1):
        try:
            response = await session.get(URL, params=params, timeout=30)
            if response.status_code in RETRYABLE_STATUSES:
                if attempt == retries:
                    response.raise_for_status()
                wait = retry_wait(response.headers.get("Retry-After"), attempt)
                LOG.warning("%s: HTTP %s, retrying in %.1fs", job.key, response.status_code, wait)
                await anyio.sleep(wait)
                continue
            # HTTP 400 is a validation failure, not evidence of missing EPG.
            response.raise_for_status()
            return validate_payload(response.json(), job)
        except (niquests.Timeout, niquests.ConnectionError) as error:
            if attempt == retries:
                raise
            wait = retry_wait(None, attempt)
            LOG.warning("%s: %s, retrying in %.1fs", job.key, error, wait)
            await anyio.sleep(wait)
    raise RuntimeError("Unexpected retry loop exit")


async def worker(index, receiver, session, output, retries, pause, counters, failures):
    async with receiver:
        async for job in receiver:
            path = output / job.key
            if await anyio.to_thread.run_sync(existing_valid, path, job):
                counters["skipped"] += 1
                continue
            try:
                payload = await fetch(session, job, retries)
                payload["_request"] = job.metadata()
                await anyio.to_thread.run_sync(write_atomic, path, payload)
                counters["completed"] += 1
                n = sum(len(day["programs"]) for days in payload["data"].values() for day in days)
                LOG.info("OK %s channels=%d programs=%d", job.key, len(job.ids), n)
            except Exception as exc:
                counters["failed"] += 1
                failures.append({"job": job.metadata(), "error": repr(exc)})
                LOG.error("FAILED %s: %s", job.key, exc)
            await anyio.sleep(pause)


async def run(args):
    ids = catalog_channels(args.catalog)
    if not ids:
        raise ValueError("No EPG-capable channels found")
    jobs = list(make_jobs(ids, args.start, args.end))
    total_days = (args.end - args.start).days + 1
    LOG.info("%d channels, %d days, %d channel-days, %d jobs",
             len(ids), total_days, len(ids) * total_days, len(jobs))
    args.output.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        for job in jobs[:12]:
            LOG.info("PLAN %s channels=%d days=%d", job.key, len(job.ids), (job.last-job.first).days+1)
        return
    counters = {"completed": 0, "skipped": 0, "failed": 0}
    failures = []
    send, receive = anyio.create_memory_object_stream(2 * args.concurrency)
    async with niquests.AsyncSession(headers={"Accept": "application/json"},
                                      multiplexed=False) as session:
        async with anyio.create_task_group() as tg:
            for i in range(args.concurrency):
                tg.start_soon(worker, i, receive.clone(), session, args.output,
                              args.retries, args.pause, counters, failures)
            await receive.aclose()
            async with send:
                for job in jobs:
                    await send.send(job)
    if failures:
        file = args.output / "failures.jsonl"
        with file.open("a", encoding="utf-8") as f:
            for failure in failures:
                f.write(json.dumps(failure, ensure_ascii=False) + "\n")
    LOG.info("FINISHED %s / total=%d", counters, len(jobs))
    if counters["failed"]:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("channels.json"))
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 5, 3))
    parser.add_argument("--end", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output", type=Path, default=Path("out/vtvgo/raw"))
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--pause", type=float, default=0.5, help="Per-worker pause in seconds")
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if args.end < args.start or args.concurrency < 1 or args.retries < 1 or args.pause < 0:
        parser.error("Invalid date range, concurrency, retries, or pause")
    anyio.run(run, args, backend="asyncio", backend_options={"use_uvloop": True})


if __name__ == "__main__":
    main()

