import time
from datetime import date

import niquests as requests

URL = "https://apigateway.vtvcab.vn/mycab/api/v2/landing-page/broadcast_list"
PARAM = "date"

session = requests.Session()


def debug(*msg: str):
    if RUNNING_FROM_MAIN:
        print("[DEBUG]", *msg)


def check(day: date) -> bool:
    response = session.get(URL, params={PARAM: day.isoformat()}, timeout=15)

    if response.status_code == 200:
        debug(f"Found supported date: {day.isoformat()}")
        return True

    if response.status_code == 429:
        raise RuntimeError("Rate limited")

    if response.status_code == 500:
        debug(f"Out of range: {day.isoformat()}")
        return False  # Assumption: outside supported range

    raise RuntimeError(f"Unexpected HTTP {response.status_code}")


def find_max_date(start=date(2022, 12, 31)):
    lo = start.toordinal()
    step = 1

    # Phase 1: Exponential search
    while True:
        hi = min(lo + step, date.max.toordinal())

        time.sleep(0.5)
        debug("Attempting to check date:", date.fromordinal(hi).isoformat())
        if not check(date.fromordinal(hi)):
            debug("Found upper bound:", date.fromordinal(hi).isoformat())
            break

        lo = hi
        step *= 2

        if lo == date.max.toordinal():
            return date.max

    # Phase 2: Binary search
    while hi - lo > 1:
        mid = (lo + hi) // 2
        debug(
            "Finding dates between:",
            date.fromordinal(lo).isoformat(),
            "and",
            date.fromordinal(hi).isoformat(),
        )

        time.sleep(0.5)
        if check(date.fromordinal(mid)):
            lo = mid
        else:
            hi = mid

    return date.fromordinal(lo)


RUNNING_FROM_MAIN = __name__ == "__main__"
if RUNNING_FROM_MAIN:
    print("Maximum supported date:", find_max_date())
