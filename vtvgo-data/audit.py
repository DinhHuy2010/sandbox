
import json
from collections import defaultdict
from pathlib import Path

root = Path("out/vtvgo/raw")

total_programs = 0
total_files = 0
coverage = defaultdict(lambda: {
    "programs": 0,
    "first": None,
    "last": None,
})

for path in sorted(root.glob("group_*/*.json")):
    data = json.loads(path.read_text("utf-8"))
    total_files += 1

    for channel_id, entries in data.get("data", {}).items():
        for entry in entries:
            programs = entry.get("programs") or []
            if not programs:
                continue

            dt = entry["date"]
            item = coverage[channel_id]

            item["programs"] += len(programs)
            item["first"] = min(item["first"] or dt, dt)
            item["last"] = max(item["last"] or dt, dt)
            total_programs += len(programs)

print("JSON files:", total_files)
print("Actual program records:", total_programs)
print("Channels with data:", len(coverage))

for channel, info in sorted(coverage.items()):
    print(
        channel,
        info["first"],
        info["last"],
        info["programs"],
    )
