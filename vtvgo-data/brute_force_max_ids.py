import json
from datetime import date
from pathlib import Path

from niquests import HTTPError

import vtvgo_epg

catalog = json.loads(Path("channels.json").read_text("utf-8"))

channels = {
    ch["id"]: ch["name"]
    for group in catalog["data"]
    for ch in group.get("channels", [])
    if ch.get("epgChannelId") and ch.get("enabled")
    # and group["id"]
    # == "6a95b9e9cc5bb9fa8eeac4db"  # restirct so we have a good working channels list
}
ids = list(channels.keys())


def probe(ids):
    try:
        vtvgo_epg.get_channel_epg(ids, date.today())
    except HTTPError as e:
        if e.response.status_code == 400:
            print(f"Rejected {len(ids)} channels: {e}")
            return False
        raise

    else:
        print(f"Accepted {len(ids)} channels")
        return True


def discover_channel_limit(channel_ids, probe):
    """
    probe(ids) -> True if accepted, False if rejected.

    Assumes all IDs are individually valid and
    acceptance is monotonic with channel count.
    """

    # Phase 1: Exponential search
    last_good = 0
    count = 1

    while count <= min(len(channel_ids), 120):
        print(f"--> Trying {count} channels")

        if not probe(channel_ids[:count]):
            break

        last_good = count
        count *= 2

    upper = min(count, len(channel_ids), 121)

    if last_good == len(channel_ids):
        return last_good

    # Phase 2: Binary search
    low = last_good
    high = upper

    while high - low > 1:
        mid = (low + high) // 2

        print(f"--> Trying {mid} channels")

        if probe(channel_ids[:mid]):
            low = mid
        else:
            high = mid

    return low


if __name__ == "__main__":
    print(f"Max channels: {discover_channel_limit(ids, probe)}")
