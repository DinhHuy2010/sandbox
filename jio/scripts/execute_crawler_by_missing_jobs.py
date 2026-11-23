import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import anyio
import typer

from jio.crawler.config import Config
from jio.crawler.core import Crawler
from jio.logging_infra import get_logger


@dataclass
class DiagDataJobSpec:
    diag_path: Path

    def generate_jobs(self):
        with self.diag_path.open("r", encoding="utf-8") as f:
            for line in f:
                x = json.loads(line)
                yield (x["channel_id"], date.fromisoformat(x["date_requested"]))


def main(
    diagnostics_data: Path = typer.Argument(
        ..., help="Path to the diagnostics data file."
    ),
    root: Path = typer.Argument(..., help="Root directory for storing data."),
    max_workers: int = typer.Option(30, help="Maximum number of concurrent workers."),
    crawler_logs: str = typer.Option(
        "logs/crawler.jsonl", help="Path to logs in JSON format"
    ),
) -> None:
    """Execute the crawler with the specified configuration."""
    with get_logger("jio/execute_crawler", crawler_logs) as logger:
        config = Config(root=anyio.Path(root), max_workers=max_workers)
        crawler = Crawler(config=config, logger=logger)
        spec = DiagDataJobSpec(diag_path=diagnostics_data)
        anyio.run(
            crawler.crawl,
            spec,
            backend="asyncio",
            backend_options={"use_uvloop": True},
        )


if __name__ == "__main__":
    typer.run(main)
