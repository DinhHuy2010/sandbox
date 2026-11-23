#!/usr/bin/env python3
"""Find missing JioTV channel/day files using earliest_epg.json and a SQLite manifest.

Assumptions:
  * earliest_epg.json is a mapping of channel IDs to ISO start dates, or
    to objects containing an ISO date under a recognized key.
  * SQLite contains files(channel_id, requested_date, ...).
  * Each channel requires every date from its earliest EPG date to --end-date,
    inclusive. HTTP 404 days are reported as missing, not automatically excluded.

Example:
  python scripts/find_missing_jobs.py earliest_epg.json out/simple_manifest.db \
      --output out/missing_jobs.jsonl --end-date 2026-11-23
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

DATE_FIELDS = ("earliest_date", "earliest_epg", "start_date", "first_date", "date")


def get_start_date(value: object, channel_id: str) -> date:
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    if isinstance(value, dict):
        for key in DATE_FIELDS:
            candidate = value.get(key)
            if isinstance(candidate, str):
                return date.fromisoformat(candidate[:10])
    raise ValueError(
        f"Channel {channel_id}: expected ISO date string or object containing "
        f"one of {DATE_FIELDS}; got {value!r}"
    )


def load_buckets(path: Path) -> dict[int, date]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object mapping channel IDs to earliest dates")
    return {int(k): get_start_date(v, str(k)) for k, v in data.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("earliest_epg", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("missing_jobs.jsonl"))
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=datetime.now(UTC).date(),
        help="Inclusive UTC date, default current UTC date",
    )
    args = parser.parse_args()

    starts = load_buckets(args.earliest_epg)
    uri = f"{args.manifest.resolve().as_uri()}?mode=ro"
    expected = 0
    missing = 0
    indexed = 0
    per_channel: dict[int, int] = {}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with (
        sqlite3.connect(uri, uri=True) as conn,
        args.output.open("w", encoding="utf-8") as output,
    ):
        # SQLite row lookup is sufficient at this scale. A cached 17 MB index makes
        # this far cheaper than inspecting ~450K JSON payloads.
        sql = "SELECT 1 FROM files WHERE channel_id=? AND requested_date=? LIMIT 1"
        for channel_id, start in sorted(starts.items()):
            if start > args.end_date:
                continue
            current = start
            while current <= args.end_date:
                expected += 1
                if (
                    conn.execute(sql, (channel_id, current.isoformat())).fetchone()
                    is None
                ):
                    output.write(
                        json.dumps(
                            {
                                "channel_id": channel_id,
                                "date_requested": current.isoformat(),
                            }
                        )
                        + "\n"
                    )
                    missing += 1
                    per_channel[channel_id] = per_channel.get(channel_id, 0) + 1
                else:
                    indexed += 1
                current += timedelta(days=1)

    print(f"Channels: {len(starts):,}")
    print(f"Expected jobs: {expected:,}")
    print(f"Indexed jobs: {indexed:,}")
    print(f"Missing jobs: {missing:,}")
    print(f"Channels with gaps: {len(per_channel):,}")
    print(f"Output: {args.output}")
    if per_channel:
        print("Top channels with gaps:")
        for channel_id, count in sorted(
            per_channel.items(), key=lambda x: (-x[1], x[0])
        )[:10]:
            print(f"  {channel_id}: {count}")


if __name__ == "__main__":
    main()
