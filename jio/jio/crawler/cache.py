import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

import msgspec
from structlog.typing import FilteringBoundLogger

from jio.crawler.config import Config
from jio.crawler.models import DataResponse
from jio.crawler.writer import Writer

CUTOFF_AFTER = 30  # days
MAX_FRESHNESS = 48  # hours


class Cache:
    def __init__(self, config: Config, logger: FilteringBoundLogger):
        self.config = config
        self.logger = logger.bind(name="jio/crawler/cache")
        self.writer = Writer(config)
        self._db = None

    async def ensure(self) -> None:
        await self.config.ensure()

    @property
    def simple_manifest_path(self) -> Path:
        return self.config.root / "simple_manifest.db"

    def _open(self):
        if self._db is not None:
            return self._db
        self._db = sqlite3.connect(
            f"file:{self.simple_manifest_path}?mode=ro", uri=True
        )
        return self._db

    def _is_staled(self, channel_id: int, date_requested: date) -> bool | None:
        row = (
            self._open()
            .execute(
                "SELECT mtime_ns FROM files WHERE channel_id=? AND requested_date=?",
                (channel_id, date_requested.isoformat()),
            )
            .fetchone()
        )

        if row is None:
            # doesn't exist
            return None

        now = datetime.now(UTC)

        # Historical EPG is permanent
        if (now.date() - date_requested).days >= CUTOFF_AFTER:
            return False

        # Recent EPG expires after MAX_FRESHNESS hours
        mtime_ns = row[0]
        mtime = datetime.fromtimestamp(mtime_ns / 1e9, tz=UTC)

        return (now - mtime).total_seconds() / 3600 > MAX_FRESHNESS

    async def get(self, channel_id: int, date_requested: date) -> DataResponse | None:
        if self._is_staled(channel_id, date_requested):
            await self.logger.awarning(
                "Cache entry is stale, entry will be evicted",
                channel_id=channel_id,
                date_requested=date_requested.isoformat(),
            )
            return None
        raw_data_file = (
            self.config.data_dir
            / f"channel_id={channel_id}/month={date_requested.strftime('%Y-%m')}/{date_requested.isoformat()}.json"
        )
        if not await raw_data_file.exists():
            return None
        async with await raw_data_file.open("rb") as f:
            response = msgspec.json.decode(await f.read(), type=DataResponse)
        return response

    async def evict(self, response: DataResponse) -> bool:
        await self.remove_resp(response.about.channel_id, response.about.date_requested)

    async def remove_resp(self, channel_id: int, date_requested: date) -> None:
        raw_data_file = (
            self.config.data_dir
            / f"channel_id={channel_id}/month={date_requested.strftime('%Y-%m')}/{date_requested.isoformat()}.json"
        )
        await raw_data_file.unlink(missing_ok=True)

    async def add(self, resp: DataResponse) -> None:
        await self.writer.write(resp)

    def contains(self, channel_id: int, date_requested: date) -> bool:
        return self._is_staled(channel_id, date_requested) is False
