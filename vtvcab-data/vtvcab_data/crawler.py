from datetime import date
from pathlib import Path

import anyio
import niquests
import structlog

from vtvcab_data.lib import pull_listing
from vtvcab_data.reader import Reader
from vtvcab_data.writer import Writer

SEMAPHORE_LIMIT = 50
MAX_ATTEMPTS_BEFORE_GIVE_UP = 5


class Crawler:
    def __init__(self, root: Path):
        self.root = root
        self.reader = Reader(self.root)
        self.writer = Writer(self.root)
        self.client = niquests.AsyncSession()
        self.sem = anyio.Semaphore(SEMAPHORE_LIMIT)
        self.log: structlog.stdlib.BoundLogger = structlog.get_logger()
        self.stats = {"ok": 0, "skipped": 0, "failed": 0, "total": 0}

    def init(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with open(self.root / ".gitignore", "w") as f:
            f.write("# ignore all\n*")
        self.writer.init()

    async def worker(self, date: date):
        """
        Worker function to pull data for a specific date and write it to disk.
        """
        log = self.log.bind(name="vtvcab_data/crawler/worker", date=date.isoformat())
        if await self.reader.should_refresh(date):
            async with self.sem:
                for _ in range(MAX_ATTEMPTS_BEFORE_GIVE_UP):
                    try:
                        response = await pull_listing(date, self.client)
                        break
                    except Exception:
                        await log.aexception("Failed to pull data, retrying!")
                else:
                    await log.aerror(
                        "Failed to pull data after multiple attempts, skipping."
                    )
                    self.stats["failed"] += 1
                    return
                try:
                    await self.writer.ingest(response)
                except Exception:
                    await log.aexception("Failed to write data to disk!")
                    self.stats["failed"] += 1
                    return
                await log.ainfo("Pulled data from API and wrote to disk.")
                self.stats["ok"] += 1
        else:
            await log.ainfo("Skipping pull from API, data is up to date.")
            self.stats["skipped"] += 1

    async def crawl(self, start_date: date, end_date: date):
        """
        Crawl data for a given date range.
        """
        log = self.log.bind(
            name="vtvcab_data/crawler/crawl",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        async with anyio.create_task_group() as tg:
            dates = [
                date.fromordinal(d)
                for d in range(start_date.toordinal(), end_date.toordinal() + 1)
            ]
            await log.ainfo(f"Starting crawl for {len(dates)} dates...")
            for d in dates:
                tg.start_soon(self.worker, d)
        self.stats["total"] = (
            self.stats["ok"] + self.stats["skipped"] + self.stats["failed"]
        )
        await log.ainfo("Crawl completed!", stats=self.stats)
