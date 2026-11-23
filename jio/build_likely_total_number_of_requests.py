from datetime import date

import msgspec

with open("earliest_epg.json", "rb") as f:
    data = msgspec.json.decode(f.read(), type=dict[int, date])

td = date.today()
total = 0
for channel_id, earliest in sorted(data.items()):
    total_reqs = (td - earliest).days + 1
    print(f"Channel {channel_id}: earliest={earliest}, total_reqs={total_reqs}")
    total += total_reqs
print(f"Likely total number of requests: {total} requests")
