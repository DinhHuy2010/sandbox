from collections.abc import Iterable
from datetime import date
from typing import Protocol

import msgspec
from anyio import Path

type Work = tuple[int, date]


class Config(msgspec.Struct):
    root: Path
    max_workers: int = 30

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    async def ensure(self) -> None:
        await self.root.mkdir(parents=True, exist_ok=True)
        await self.data_dir.mkdir(parents=True, exist_ok=True)
        async with await (self.root / ".gitignore").open("w") as f:
            await f.write("*\n")


class JobSpec(Protocol):
    def generate_jobs(self) -> Iterable[Work]:
        """Generate a sequence of jobs to be crawled. Each job is a tuple of (channel_id, date)."""
