from datetime import date

import niquests

SESSION = niquests.Session()
SCHEDULE_API_URL = "https://cdn.mewatch.sg/api/schedules"


def get_schedule(channel_ids: list[int], date: date) -> dict:
    # DATE MUST IN UTC!
    params = {
        "channels": ",".join(map(str, channel_ids)), # maybe multiple channels can be passed in as a comma-separated list??
        "date": date.strftime("%Y-%m-%d"),
        "duration": 24,
        "hour": 17,  # UTC
        "intersect": "true",
        "lang": "en",
        "segments": "all",
    }
    resp = SESSION.get(SCHEDULE_API_URL, params=params)
    resp.raise_for_status()
    # print(resp.request.url)
    return resp.json()

CHANNEL_5 = 97098
CHANNEL_8 = 97104
channels = get_schedule([CHANNEL_5, CHANNEL_8], date(2026, 11, 20))
# print(channels)
for channel in channels:
    print(f"====== {channel["channelId"]} ======")
    for s in channel["schedules"]:
        print(s["item"]["title"], s["startDate"], s["endDate"])
