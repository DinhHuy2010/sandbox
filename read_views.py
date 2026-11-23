import string
from collections import Counter
from pathlib import Path

from tqdm import tqdm

PATH = Path("~/trees/wikimedia").expanduser().resolve()

datafile = PATH / "pageviews-20261111-user"


BUF = 4 * 1024 * 1024  # 4 MB


def decode_hourly_counts(hourly_counts: str) -> dict[int, int]:
    out = {}
    cmap = {i: x for i, x in zip(string.ascii_uppercase, range(24))}
    current_char, nbuf = "", ""
    for c in hourly_counts:
        if c in cmap:
            if current_char:
                out[cmap[current_char]] = int(nbuf)
            current_char, nbuf = c, ""
        else:
            nbuf += c
    if current_char:
        out[cmap[current_char]] = int(nbuf)
    return out


# db = {}


# def add_entry(
#     site: str,
#     title: str,
#     page_id: str,
#     access_method: str,
#     daily_total: str,
#     hourly_counts: str,
# ):
#     if site not in db:
#         print("Creating new site entry for", site)
#         db[site] = {}
#     if page_id not in db[site]:
#         # print("Creating new page_id entry for", page_id)
#         db[site][page_id] = []
#     db[site][page_id].append(
#         {
#             "title": title,
#             "access_method": access_method,
#             "daily_total": int(daily_total),
#             "hourly_counts": decode_hourly_counts(hourly_counts),
#         }
#     )


total_daily_count = 0
total_hourly_counts = [0] * 24


def accu_hourly(hourly_counts: bytes, arr: list[int]):
    start = 0
    hour = -1

    for i, c in enumerate(hourly_counts):
        if 65 <= c <= 88:
            if hour >= 0:
                arr[hour] += int(hourly_counts[start:i])

            hour = c - 65
            start = i + 1

    if hour >= 0:
        arr[hour] += int(hourly_counts[start:])


with datafile.open("rb", buffering=BUF) as f:
    for line in tqdm(f):
        try:
            daily_total, hourly_counts = line.rsplit(b" ", 2)[-2:]
        except ValueError:
            print("Error parsing line:")
            print(repr(line))
            continue
        # add_entry(site, title, page_id, access_method, daily_total, hourly_counts)
        total_daily_count += int(daily_total)
        accu_hourly(hourly_counts, total_hourly_counts)
        # hourly_counts_dict = decode_hourly_counts(hourly_counts)
        # total_hourly_counts.update(hourly_counts_dict)

print("-- results --")
print("Total daily count:", total_daily_count)
print("-- by hour --")
for hour, value in enumerate(total_hourly_counts):
    print(f"Hour {hour}: {value}")
print(
    "Daily count == sum(hourly counts)?", total_daily_count == sum(total_hourly_counts)
)
