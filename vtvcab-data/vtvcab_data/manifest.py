import datetime
from pathlib import Path
from typing import Any

import anyio
import msgspec
import structlog

from vtvcab_data.reader import Reader


class ManifestByDay(msgspec.Struct):
    date: str
    total_entries: int
    total_channels: int
    total_seconds: float
    warnings: list[dict[str, Any]]


class Manifest(msgspec.Struct):
    by_day: dict[datetime.date, ManifestByDay]
    total_entries: int
    total_channels: int
    total_seconds: float
    generated_at: datetime.datetime


class ManifestBuilder:
    def __init__(self, root: Path):
        self.root = root
        self.async_root = anyio.Path(self.root)
        self.log: structlog.stdlib.BoundLogger = structlog.get_logger()
        self.by_days: dict[datetime.date, ManifestByDay] = {}
        self.unique_channels = set()
        self.reader = Reader(root)

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    async def manifest_by_day_worker(self, date: datetime.date) -> None:
        r = await self.reader.read(date)
        channels = r.data["data"]
        total_channels = len(channels)
        total_entries = 0
        total_seconds = 0
        self.unique_channels.update(c["channel_id"] for c in channels)
        warnings = []
        for channel in channels:
            for item in channel["items"]:
                start = datetime.datetime.fromisoformat(item["start"])
                end = datetime.datetime.fromisoformat(item["end"])
                if end < start:
                    await self.log.awarning(
                        "Invalid item with end before start",
                        date=date,
                        channel_id=channel["channel_id"],
                        item=item,
                    )
                    warnings.append(
                        {
                            "channel_id": channel["channel_id"],
                            "item": item,
                            "reason": "end before start",
                        }
                    )
                    continue
                total_entries += 1
                total_seconds += (end - start).total_seconds()
        manifest_by_day = ManifestByDay(
            date=date.isoformat(),
            total_entries=total_entries,
            total_channels=total_channels,
            total_seconds=total_seconds,
            warnings=warnings,
        )
        self.by_days[date] = manifest_by_day
        await self.log.ainfo("Processed manifest for date", date=date)

    async def build(self) -> Manifest:
        dates = await self.reader.list_dates()
        await self.log.ainfo(f"Building manifest for {len(dates)} dates...")
        async with anyio.create_task_group() as tg:
            for date in dates:
                tg.start_soon(self.manifest_by_day_worker, date)
        total_entries = sum(m.total_entries for m in self.by_days.values())
        total_channels = len(self.unique_channels)
        total_seconds = sum(m.total_seconds for m in self.by_days.values())
        manifest = Manifest(
            by_day=self.by_days,
            total_entries=total_entries,
            total_channels=total_channels,
            total_seconds=total_seconds,
            generated_at=datetime.datetime.now(datetime.UTC),
        )
        return manifest

    def save(self, manifest: Manifest) -> None:
        self.log.info("Saving manifest", path=self.manifest_path)
        with open(self.manifest_path, "wb") as f:
            f.write(msgspec.json.encode(manifest))
