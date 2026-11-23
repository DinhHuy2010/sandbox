import pathlib
from datetime import date

from msgspec import json
from tqdm import tqdm

from vtvcab_data.lib import DataResponse

p = pathlib.Path("out/")

registry = {}


def insert(registry, channel_id, title, date):
    if title not in registry[channel_id]["known_as"]:
        registry[channel_id]["known_as"][title] = [date]
    else:
        registry[channel_id]["known_as"][title].append(date)
    # registry[channel_id]["dates"].append(date)


def compress(dates: list[date]) -> list[dict]:
    # dates = list(map(date.fromisoformat, sorted(dates)))
    if not dates:
        return []
    ranges = []
    current_range = {"start": dates[0], "end": dates[0]}
    for i in range(1, len(dates)):
        cand1, cand2 = dates[i - 1], dates[i]
        if cand2 - cand1 == date.resolution:
            current_range["end"] = cand2
        else:
            ranges.append(current_range)
            current_range = {"start": cand2, "end": cand2}
    ranges.append(current_range)
    return ranges


def compute_unavailable_dates(dates: list[date]) -> list[date]:
    if not dates:
        return []

    ordinals = {d.toordinal() for d in dates}
    start, end = min(ordinals), max(ordinals)

    return [date.fromordinal(i) for i in range(start, end + 1) if i not in ordinals]


files = sorted((p / "raw").rglob("*.json"))
for f in tqdm(files):
    with open(f, "r") as infile:
        data = json.decode(infile.read(), type=DataResponse)
        channels = data.data["data"]
        for channel in channels:
            registry.setdefault(
                channel["channel_id"],
                {
                    "known_as": {},  # [{title: ..., dates: ...}]
                },
            )
            insert(
                registry,
                channel["channel_id"],
                channel["channel_title"],
                data.requested_date_listing,
            )

registry = {
    channel_id: {
        **channel_data,
        "known_as": {
            title: compress(dates) for title, dates in channel_data["known_as"].items()
        },
        "unavailable_dates": compute_unavailable_dates(
            [d for dates in channel_data["known_as"].values() for d in dates]
        ),
    }
    for channel_id, channel_data in registry.items()
}
print(json.encode(registry).decode("utf-8"))
