import time
from datetime import date

import niquests as requests

URL = "https://apigateway.vtvcab.vn/mycab/api/v2/landing-page/broadcast_list"
PARAM = "date"

session = requests.Session()


def check(day):
    response = session.get(URL, params={PARAM: day.isoformat()}, timeout=15)

    print(day, response.status_code)

    if response.status_code == 200:
        return True

    if response.status_code == 429:
        raise RuntimeError("Rate limited")

    if response.status_code == 500:
        return False  # Assumption: outside supported range

    raise RuntimeError(f"Unexpected HTTP {response.status_code}")


def find_max_date(start=date(2022, 12, 31)):
    lo = start.toordinal()
    step = 1

    # Phase 1: Exponential search
    while True:
        hi = min(lo + step, date.max.toordinal())

        time.sleep(0.5)
        if not check(date.fromordinal(hi)):
            break

        lo = hi
        step *= 2

        if lo == date.max.toordinal():
            return date.max

    # Phase 2: Binary search
    while hi - lo > 1:
        mid = (lo + hi) // 2

        time.sleep(0.5)
        if check(date.fromordinal(mid)):
            lo = mid
        else:
            hi = mid

    return date.fromordinal(lo)


print("Maximum supported date:", find_max_date())
