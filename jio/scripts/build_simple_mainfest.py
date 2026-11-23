import os
import sqlite3
from datetime import date
from pathlib import Path

import typer

TABLE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS files (
        channel_id INTEGER NOT NULL,
        requested_date TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        mtime_ns INTEGER NOT NULL,
        PRIMARY KEY (channel_id, requested_date)
    ) WITHOUT ROWID
"""


def build_index(root: Path, database: Path) -> None:
    print("--> Building index")
    with sqlite3.connect(database) as conn:
        conn.execute(TABLE_SCHEMA)
        rows = []

        with os.scandir(root / "data") as channels:
            for channel in channels:
                if not channel.is_dir():
                    continue
                if not channel.name.startswith("channel_id="):
                    continue

                channel_id = int(channel.name.split("=", 1)[1])

                with os.scandir(channel.path) as months:
                    for month in months:
                        if not month.is_dir():
                            continue

                        with os.scandir(month.path) as files:
                            for entry in files:
                                if not entry.is_file():
                                    continue
                                if not entry.name.endswith(".json"):
                                    continue

                                try:
                                    requested_date = date.fromisoformat(
                                        entry.name.removesuffix(".json")
                                    )
                                except ValueError:
                                    continue

                                stat = entry.stat()

                                rows.append(
                                    (
                                        channel_id,
                                        requested_date.isoformat(),
                                        stat.st_size,
                                        stat.st_mtime_ns,
                                    )
                                )

        conn.executemany(
            """
            INSERT OR REPLACE INTO files VALUES (?, ?, ?, ?)""",
            rows,
        )


def main(
    root: Path = typer.Argument(..., help="Root directory to scan"),
    database: Path = typer.Argument(..., help="SQLite database file to create"),
) -> None:
    build_index(root, database)


if __name__ == "__main__":
    typer.run(main)
