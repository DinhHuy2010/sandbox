from datetime import date
from pathlib import Path

import anyio
import typer

from vtvcab_data.crawler import Crawler


def main(
    date_range: str = typer.Argument(
        ..., help="Date range in the format YYYY-MM-DD:YYYY-MM-DD"
    ),
    directory: Path = typer.Argument(..., help="Directory to store the ingested data"),  # noqa: B008
):
    """
    Ingest data for a given date range.
    """

    start_date_str, end_date_str = date_range.split(":")
    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)

    crawler = Crawler(root=directory)
    crawler.init()

    anyio.run(
        crawler.crawl,
        start_date,
        end_date,
        backend="asyncio",
        backend_options={"use_uvloop": True},
    )


if __name__ == "__main__":
    typer.run(main)
