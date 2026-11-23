import datetime
import pathlib
import re
from zoneinfo import ZoneInfo

import orjson
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

BASE_PATH = pathlib.Path("out-snapshot-20261102-074800/out/raw").resolve()
with (BASE_PATH / "status.json").open("rb") as f:
    STATUS = orjson.loads(f.read())
# print(f"--> Total files: {status['progress']['total']}")
BATCH_SIZE = 100_000
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
CRAWL_DATE = datetime.datetime.fromisoformat(STATUS["started_at"]).astimezone(VIETNAM_TZ).date()
EXPECTED_FILE_COUNT = STATUS["progress"]["total"]


DATE_PATTERN = re.compile(r"^/Date\((-?\d+)(?:[+-]\d{4})?\)/$")

SCHEMA = pa.schema(
    [
        pa.field("filename_source", pa.string()),
        pa.field("is_future", pa.bool_()),
        pa.field("channel_id", pa.int32()),
        pa.field("date_aspnet_str", pa.string()),
        pa.field("start_time", pa.string()),
        pa.field("end_time", pa.string()),
        pa.field("name", pa.string()),
        pa.field("short_descriptor", pa.string()),
        pa.field("extended_descriptor", pa.string()),
        pa.field("hot", pa.bool_()),
    ]
)


def parse_aspnet_date(value: str) -> datetime.date:
    match = DATE_PATTERN.fullmatch(value)

    if match is None:
        raise ValueError(f"Invalid ASP.NET date: {value!r}")

    milliseconds = int(match.group(1))

    dt = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC) + datetime.timedelta(
        milliseconds=milliseconds
    )

    return dt.astimezone(VIETNAM_TZ).date()


def flush_batch(writer, rows):
    if not rows:
        return

    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    writer.write_table(table, row_group_size=BATCH_SIZE)
    rows.clear()


def export():
    OUTPUT_PATH = pathlib.Path("out/sctv-out-snapshot-20261102-074800.parquet").resolve()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    files = BASE_PATH.glob("data/*/*/*.json")

    rows = []
    file_count = 0
    event_count = 0

    with pq.ParquetWriter(
        OUTPUT_PATH,
        schema=SCHEMA,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
    ) as writer:
        for path in tqdm(files, desc="Exporting SCTV", unit="file", total=EXPECTED_FILE_COUNT):
            file_count += 1

            with path.open("rb") as f:
                response = orjson.loads(f.read())

            schedule = response.get("LichPhatSong")

            if not schedule:
                continue

            raw_date = schedule["Date"]
            broadcast_date = parse_aspnet_date(raw_date)
            is_future = broadcast_date > CRAWL_DATE

            channel_id = schedule["ChannelId"]

            for event in schedule.get("EventList") or []:
                rows.append(
                    {
                        "filename_source": path.relative_to(BASE_PATH).as_posix(),
                        "is_future": is_future,
                        "channel_id": channel_id,
                        "date_aspnet_str": raw_date,
                        "start_time": event.get("StartTime"),
                        "end_time": event.get("EndTime"),
                        "name": event.get("Name"),
                        "short_descriptor": event.get("ShortDescriptor"),
                        "extended_descriptor": event.get("ExtendedDescriptor"),
                        "hot": event.get("Hot"),
                    }
                )

                event_count += 1

                if len(rows) >= BATCH_SIZE:
                    flush_batch(writer, rows)

        flush_batch(writer, rows)

    print(f"Files scanned: {file_count:,}")
    print(f"Events exported: {event_count:,}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Size: {OUTPUT_PATH.stat().st_size / 1024**2:.2f} MiB")


if __name__ == "__main__":
    export()


