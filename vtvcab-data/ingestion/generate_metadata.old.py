import datetime
import pathlib

import orjson
from tqdm import tqdm


def calcuate_total_number_of_seconds(items):
    def total_seconds(item):
        start = datetime.datetime.fromisoformat(item["start"])
        end = datetime.datetime.fromisoformat(item["end"])
        if start > end:
            print("************************")
            print("STOP!")
            print(f"Start time {start} is after end time {end} for item: {item}")
            print((end - start).total_seconds())
            return 0
            # raise ValueError(f"Start time {start} is after end time {end} for item: {item}")
        return int((end - start).total_seconds())

    return sum(total_seconds(item) for item in items)


BASE_DIR = pathlib.Path("out/raw").resolve()
OUT_DIR = pathlib.Path("out").resolve()
CURRENT_DATE = datetime.date.today()
unique_channel_identifiers = set()
total_programs = 0
total_seconds = 0
print("--> Listing paths...")
paths = sorted(BASE_DIR.glob("*.json"))

global_meta = {"by-date": {}}

print("--> Processing paths...")
for path in tqdm(paths):
    date = datetime.date.fromisoformat(path.stem)
    data = orjson.loads(path.read_bytes())
    channels = data["data"]
    unique_channel_identifiers.update([channel["channel_id"] for channel in channels])
    items = [item for channel in channels for item in channel["items"]]
    total = len(items)
    total_programs += total
    total_seconds_for_items = calcuate_total_number_of_seconds(items)
    total_seconds += total_seconds_for_items
    meta = {
        "channels": len(channels),
        "entries": total,
        "is_partial": date > CURRENT_DATE,
        "total_seconds": total_seconds_for_items,
    }
    global_meta["by-date"][path.stem] = meta
print("--> Writing metadata.json...")
global_meta.update(
    {
        "channels": sorted(unique_channel_identifiers),
        "total_channels": len(unique_channel_identifiers),
        "total_entries": total_programs,
        "total_seconds": total_seconds,
    }
)
global_meta["last_updated"] = datetime.datetime.now(tz=datetime.UTC).isoformat()
# with open(OUT_DIR / "metadata.json", "wb") as f:
#     f.write(orjson.dumps(global_meta, option=orjson.OPT_INDENT_2))
