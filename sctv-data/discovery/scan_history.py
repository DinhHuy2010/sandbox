
#!/usr/bin/env python3
"""
SCTV Historical EPG Boundary Scanner

Scans every channel, every day in a specified date range.

Outputs:
  sctv_epg_probes.csv   - All probe results
  sctv_epg_summary.json - Per-channel historical coverage summary

Resume:
  Existing probe results are reused automatically.
"""

import csv
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
from threading import Lock

from libsctv import fetch_epg, fetch_channels


START_DATE = date(2014, 12, 1)
END_DATE = date(2015, 1, 10)

MAX_WORKERS = 4
MAX_RETRIES = 3
RETRY_DELAY = 1.0
SUSTAINED_DAYS = 7

CSV_PATH = Path("sctv_epg_probes.csv")
JSON_PATH = Path("sctv_epg_summary.json")

lock = Lock()

FIELDS = [
    "channel_id",
    "channel_name",
    "date",
    "status",
    "event_count",
    "error",
]


def iter_dates(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def load_channels():
    result = fetch_channels()
    return {
        int(ch["Ma"]): ch["Ten"]
        for ch in result["DSKenh"]
    }


def load_existing():
    records = {}

    if not CSV_PATH.exists():
        return records

    with CSV_PATH.open(
        "r", encoding="utf-8", newline=""
    ) as file:
        for row in csv.DictReader(file):
            key = (int(row["channel_id"]), row["date"])
            row["channel_id"] = int(row["channel_id"])
            row["event_count"] = int(row["event_count"])
            records[key] = row

    return records


def probe(channel_id, channel_name, day):
    date_str = day.isoformat()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = fetch_epg(channel_id, date_str)
            epg = response.get("LichPhatSong")

            if isinstance(epg, dict):
                events = epg.get("EventList") or []
                count = len(events)

                status = (
                    "VALID" if count > 0 else "EMPTY"
                )
            else:
                count = 0
                status = "MISSING"

            return {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "date": date_str,
                "status": status,
                "event_count": count,
                "error": "",
            }

        except Exception as exc:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                return {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "date": date_str,
                    "status": "ERROR",
                    "event_count": 0,
                    "error": repr(exc),
                }


def find_sustained_start(rows, days=7):
    valid_dates = {
        date.fromisoformat(row["date"])
        for row in rows
        if row["status"] == "VALID"
    }

    if not valid_dates:
        return None

    for start in sorted(valid_dates):
        if all(
            start + timedelta(days=i) in valid_dates
            for i in range(days)
        ):
            return start.isoformat()

    return None


def build_summary(records, channels):
    grouped = defaultdict(list)

    for row in records.values():
        grouped[row["channel_id"]].append(row)

    summary = {}

    for channel_id, channel_name in channels.items():
        rows = sorted(
            grouped[channel_id],
            key=lambda r: r["date"],
        )

        valid = [
            row for row in rows
            if row["status"] == "VALID"
        ]

        summary[str(channel_id)] = {
            "channel_name": channel_name,
            "earliest_event_date": (
                valid[0]["date"] if valid else None
            ),
            "earliest_sustained_coverage_date": (
                find_sustained_start(
                    rows, SUSTAINED_DAYS
                )
            ),
            "valid_days": len(valid),
            "missing_days": sum(
                r["status"] == "MISSING"
                for r in rows
            ),
            "empty_days": sum(
                r["status"] == "EMPTY"
                for r in rows
            ),
            "error_days": sum(
                r["status"] == "ERROR"
                for r in rows
            ),
            "total_events": sum(
                r["event_count"]
                for r in valid
            ),
        }

    return summary


def save_summary(records, channels):
    summary = {
        "scan_start": START_DATE.isoformat(),
        "scan_end": END_DATE.isoformat(),
        "sustained_days": SUSTAINED_DAYS,
        "channels": build_summary(records, channels),
    }

    temp = JSON_PATH.with_suffix(".json.tmp")
    temp.write_text(
        json.dumps(
            summary,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    temp.replace(JSON_PATH)


def main():
    channels = load_channels()
    records = load_existing()

    # Retry previous errors, but reuse successful probes.
    tasks = [
        (channel_id, name, day)
        for channel_id, name in channels.items()
        for day in iter_dates(START_DATE, END_DATE)
        if (
            (channel_id, day.isoformat()) not in records
            or records[
                (channel_id, day.isoformat())
            ]["status"] == "ERROR"
        )
    ]

    print(f"Channels: {len(channels)}")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Existing records: {len(records)}")
    print(f"Pending requests: {len(tasks)}")

    file_exists = CSV_PATH.exists()

    with CSV_PATH.open(
        "a", encoding="utf-8", newline=""
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=FIELDS
        )

        if not file_exists or CSV_PATH.stat().st_size == 0:
            writer.writeheader()

        with ThreadPoolExecutor(
            max_workers=MAX_WORKERS
        ) as executor:
            futures = [
                executor.submit(probe, *task)
                for task in tasks
            ]

            for completed, future in enumerate(
                as_completed(futures), start=1
            ):
                row = future.result()
                key = (
                    row["channel_id"],
                    row["date"],
                )

                with lock:
                    records[key] = row
                    writer.writerow(row)
                    file.flush()

                if (
                    completed % 50 == 0
                    or completed == len(tasks)
                ):
                    print(
                        f"[{completed}/{len(tasks)}] "
                        f"Last: {row['channel_name']} "
                        f"{row['date']} "
                        f"{row['status']} "
                        f"({row['event_count']} events)"
                    )

                    save_summary(records, channels)

    save_summary(records, channels)

    summary = build_summary(records, channels)

    print("\n=== HISTORICAL EPG SUMMARY ===")

    for channel_id, info in summary.items():
        print(
            f"{channel_id:>3} "
            f"{info['channel_name'][:24]:24} "
            f"earliest={str(info['earliest_event_date']):10} "
            f"sustained={str(info['earliest_sustained_coverage_date']):10} "
            f"valid={info['valid_days']:2} "
            f"events={info['total_events']}"
        )

    print(f"\nSaved: {CSV_PATH}")
    print(f"Saved: {JSON_PATH}")


if __name__ == "__main__":
    main()
