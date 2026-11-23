#!/usr/bin/env python3
"""Convert JioTV per-channel/day raw JSON archive to bounded-memory ZSTD Parquet.

Usage:
    uv add pyarrow msgspec
    uv run python scripts/jio_json_to_parquet.py out/data out/parquet --batch-rows 50000

The output directory must not already contain files. The raw JSON is never modified.
On failure, keep the raw archive and rerun into a NEW empty output directory.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import msgspec
import pyarrow as pa
import pyarrow.parquet as pq

# Schema is pinned instead of inferred from the first batch. Missing fields become null.
# Unexpected fields remain available in extra_json.
_FIELDS = [
    ("srno", pa.int64()),
    ("showtime", pa.string()),
    ("serverDate", pa.string()),
    ("showname", pa.string()),
    ("description", pa.string()),
    ("director", pa.string()),
    ("starCast", pa.string()),
    ("endtime", pa.string()),
    ("duration", pa.int32()),
    ("episode_num", pa.int32()),
    ("willRepeat", pa.bool_()),
    ("episode_desc", pa.string()),
    ("showCategory", pa.string()),
    ("showGenre", pa.list_(pa.string())),
    ("showId", pa.string()),
    ("serverEpoch", pa.int64()),
    ("startTime", pa.int32()),
    ("showLanguageId", pa.int32()),
    ("showCategoryId", pa.int32()),
    ("renderImage", pa.bool_()),
    ("episodeThumbnail", pa.string()),
    ("episodePoster", pa.string()),
    ("isLiveAvailable", pa.bool_()),
    ("canRecord", pa.bool_()),
    ("canRecordStb", pa.bool_()),
    ("isCatchupAvailable", pa.bool_()),
    ("stbCatchupAvailable", pa.bool_()),
    ("isDownloadable", pa.bool_()),
    ("startEpoch", pa.int64()),
    ("endEpoch", pa.int64()),
    ("pcr", pa.string()),
    ("channel_name", pa.string()),
    ("is_premium", pa.bool_()),
    ("plan_type", pa.string()),
    ("business_type", pa.string()),
    ("channel_id", pa.int32()),
    ("showGenreId", pa.int32()),
    ("isPastEpisode", pa.bool_()),
    ("twitter_handle", pa.string()),
    ("keywords", pa.list_(pa.string())),
    ("premiumText", pa.string()),
    ("isCam", pa.int32()),
]
KNOWN = {key for key, _ in _FIELDS}
PROGRAM_SCHEMA = pa.schema(
    [
        pa.field("requested_date", pa.string()),
        pa.field("source_file", pa.string()),
        *(pa.field(k, t) for k, t in _FIELDS),
        pa.field("extra_json", pa.string()),
    ]
)
DAY_SCHEMA = pa.schema(
    [
        ("requested_date", pa.string()),
        ("channel_id", pa.int32()),
        ("source_file", pa.string()),
        ("epg_count", pa.int32()),
        ("last_crawl", pa.string()),
        ("about_json", pa.string()),
        ("channel_metadata_json", pa.string()),
    ]
)


def compact_json(obj: object) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def output_batch(
    rows: list[dict],
    target: Path,
    schema: pa.Schema,
    next_part: dict[str, int],
    level: int,
) -> None:
    if not rows:
        return
    months: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        months[row["requested_date"][:7]].append(row)
    for month, values in months.items():
        folder = target / f"month={month}"
        folder.mkdir(parents=True, exist_ok=True)
        n = next_part.get(month, 0)
        path = folder / f"part-{n:06d}.parquet"
        table = pa.Table.from_pylist(values, schema=schema)
        pq.write_table(
            table,
            path,
            compression="zstd",
            compression_level=level,
            use_dictionary=True,
            row_group_size=min(100_000, len(values)),
        )
        next_part[month] = n + 1


def run(src: Path, dst: Path, batch_rows: int, level: int) -> None:
    if not src.is_dir():
        raise ValueError(f"Missing source directory: {src}")
    if dst.exists() and any(dst.iterdir()):
        raise ValueError(f"Output directory is not empty: {dst}. Use a NEW directory.")
    dst.mkdir(parents=True, exist_ok=True)
    with (dst / ".gitignore").open("w") as f:
        f.write("*\n")

    program_rows: list[dict] = []
    day_rows: list[dict] = []
    program_part: dict[str, int] = {}
    day_part: dict[str, int] = {}
    files = entries = 0
    started = time.monotonic()

    for path in src.rglob("*.json"):
        relative = str(path.relative_to(src))
        doc = msgspec.json.decode(path.read_bytes())
        if not isinstance(doc, dict) or not isinstance(doc.get("raw_data"), dict):
            raise ValueError(f"Unexpected response envelope in {path}")
        raw = doc["raw_data"]
        epg = raw.get("epg")
        if not isinstance(epg, list):
            raise ValueError(f"Missing/invalid raw_data.epg in {path}")
        about = doc.get("about")
        if not isinstance(about, dict):
            raise ValueError(f"Missing about metadata in {path}")
        requested_date = about.get("date_requested")
        channel_id = about.get("channel_id")
        if not isinstance(requested_date, str) or not isinstance(channel_id, int):
            raise ValueError(f"Missing channel/date metadata in {path}")

        day_rows.append(
            {
                "requested_date": requested_date,
                "channel_id": channel_id,
                "source_file": relative,
                "epg_count": len(epg),
                "last_crawl": doc.get("last_crawl"),
                "about_json": compact_json(about),
                "channel_metadata_json": compact_json(
                    {k: v for k, v in raw.items() if k != "epg"}
                ),
            }
        )
        for program in epg:
            if not isinstance(program, dict):
                raise ValueError(f"Non-object EPG entry in {path}")
            row = {
                "requested_date": requested_date,
                "source_file": relative,
                **{k: program.get(k) for k in KNOWN},
                "extra_json": compact_json(
                    {k: v for k, v in program.items() if k not in KNOWN}
                ),
            }
            program_rows.append(row)
        files += 1
        entries += len(epg)

        if len(program_rows) >= batch_rows:
            output_batch(
                program_rows, dst / "programs", PROGRAM_SCHEMA, program_part, level
            )
            program_rows.clear()
        if len(day_rows) >= batch_rows:
            output_batch(day_rows, dst / "days", DAY_SCHEMA, day_part, level)
            day_rows.clear()
        if files % 10_000 == 0:
            print(
                f"files={files:,} programs={entries:,} elapsed={time.monotonic() - started:.1f}s",
                flush=True,
            )

    output_batch(program_rows, dst / "programs", PROGRAM_SCHEMA, program_part, level)
    output_batch(day_rows, dst / "days", DAY_SCHEMA, day_part, level)
    print(
        f"DONE files={files:,} programs={entries:,} elapsed={time.monotonic() - started:.1f}s",
        flush=True,
    )
    print(f"Output: {dst}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", type=Path, help="JioTV raw JSON data directory (out/data)"
    )
    parser.add_argument(
        "destination", type=Path, help="New empty Parquet output directory"
    )
    parser.add_argument("--batch-rows", type=int, default=50_000)
    parser.add_argument("--zstd-level", type=int, default=5)
    args = parser.parse_args()
    if args.batch_rows < 1:
        parser.error("--batch-rows must be >= 1")
    run(args.source, args.destination, args.batch_rows, args.zstd_level)


if __name__ == "__main__":
    main()
