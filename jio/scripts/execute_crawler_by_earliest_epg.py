from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import anyio
import msgspec
import typer

from jio.crawler.core import Config, Crawler
from jio.logging_infra import get_logger


class CrawlerBucket(msgspec.Struct):
    channel_id: int
    start_date: date
    end_date: date


@dataclass
class BucketsJobSpec:
    buckets: dict[int, CrawlerBucket]

    def generate_jobs(self):
        """Generate a sequence of jobs to be crawled. Each job is a tuple of (channel_id, date)."""
        for channel_id, bucket in self.buckets.items():
            for i in range(
                bucket.start_date.toordinal(), bucket.end_date.toordinal() + 1
            ):
                yield (channel_id, date.fromordinal(i))


def build_buckets(epg_dates: Path, end_date: str | None) -> dict[int, CrawlerBucket]:
    """Builds a dictionary of Bucket objects from the provided epg_dates.json file."""
    import json

    with epg_dates.open("r", encoding="utf-8") as f:
        data = json.load(f)

    end_date = date.fromisoformat(end_date) if end_date else date.today()

    buckets = {
        int(channel_id): CrawlerBucket(
            channel_id=channel_id,
            start_date=date.fromisoformat(d),
            end_date=min(end_date, datetime.now(UTC).date()),
        )
        for channel_id, d in data.items()
    }
    return buckets


def main(
    epg_dates: Path = typer.Argument(..., help="Path to the epg_dates.json file."),
    root: Path = typer.Argument(..., help="Root directory for storing data."),
    max_workers: int = typer.Option(30, help="Maximum number of concurrent workers."),
    end_date: str | None = typer.Option(
        None, help="Optional end date for crawling in YYYY-MM-DD format."
    ),
    crawler_logs: str = typer.Option(
        "logs/crawler.jsonl", help="Path to logs in JSON format"
    ),
) -> None:
    """Execute the crawler with the specified configuration."""
    with get_logger("jio/execute_crawler", crawler_logs) as logger:
        config = Config(root=anyio.Path(root), max_workers=max_workers)
        crawler = Crawler(config=config, logger=logger)
        buckets = build_buckets(epg_dates, end_date)
        spec = BucketsJobSpec(buckets=buckets)
        anyio.run(
            crawler.crawl,
            spec,
            backend="asyncio",
            backend_options={"use_uvloop": True},
        )


if __name__ == "__main__":
    typer.run(main)
