import datetime
import logging
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import date
from logging import getLogger
from threading import Lock
from typing import Any

from libsctv import fetch_channels, fetch_epg

logger = getLogger("sctv-data.finding_ranges")
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger.setLevel("DEBUG")
s = logging.StreamHandler()
s.setFormatter(formatter)
s.setLevel("INFO")
logger.addHandler(s)
fh = logging.FileHandler("finding_ranges.log")
fh.setFormatter(formatter)
fh.setLevel("DEBUG")
logger.addHandler(fh)


def check_exists(channel_id: int, dt: date) -> bool:
    """
    Check if the EPG data for a given channel and date exists.

    Args:
        channel_id (int): The ID of the channel.
        dt (date): The date to check.

    Returns:
        bool: True if the EPG data exists, False otherwise.
    """
    epg_data = fetch_epg(channel_id, dt)
    if epg_data["LichPhatSong"] is None:
        return False
    return epg_data["LichPhatSong"] is not None


def find_bounds(
    known_good: date,
    has_data: Callable[[date], bool],
    on_probing: Callable[[date], None] | None = None,
    on_valid: Callable[[date], None] | None = None,
    on_invalid: Callable[[date], None] | None = None,
    on_done: Callable[[date, date], None] | None = None,
    extra_info: dict | None = None,
):

    cache: dict[int, bool] = {}

    def probe(n: int) -> bool:
        on_probing and on_probing(date.fromordinal(n))
        if n not in cache:
            cache[n] = has_data(date.fromordinal(n))
        return cache[n]

    origin = known_good.toordinal()

    if not probe(origin):
        on_invalid and on_invalid(known_good)
        if extra_info:
            raise ValueError(f"Starting date has no data. Extra info: {extra_info}")
        else:
            raise ValueError("Starting date has no data")

    def find_boundary(direction: int) -> int:
        good = origin
        step = 1

        # Exponential search
        while True:
            candidate = origin + direction * step

            if not 1 <= candidate <= date.max.toordinal():
                bad = 0 if direction < 0 else date.max.toordinal() + 1
                break

            if not probe(candidate):
                bad = candidate
                on_invalid and on_invalid(date.fromordinal(bad))
                break

            good = candidate
            on_valid and on_valid(date.fromordinal(good))
            step *= 2

        # Binary search
        while abs(bad - good) > 1:
            mid = (good + bad) // 2

            if probe(mid):
                on_valid and on_valid(date.fromordinal(mid))
                good = mid
            else:
                on_invalid and on_invalid(date.fromordinal(mid))
                bad = mid

        return good

    lower = find_boundary(-1)
    upper = find_boundary(+1)

    result = date.fromordinal(lower), date.fromordinal(upper)
    on_done and on_done(*result)
    return result


class EPGRangeFinder:
    def __init__(self, known_good: date, channels: dict[int, Any]):
        self.mp = ThreadPoolExecutor(max_workers=8)
        self.known_good = known_good
        self.channels = channels
        self.tasks: list[Future[tuple[int, tuple[date, date]]]] = []
        self.results: dict[int, tuple[date, date]] = {}
        self.total_probes = 0
        self.lock = Lock()

    def count_probe(self):
        with self.lock:
            self.total_probes += 1
            if self.total_probes % 100 == 0 and self.total_probes > 0:
                logger.info(f"Total probes so far: {self.total_probes}")

    def find_ranges(self, channel_id: int):
        title = self.channels[channel_id]["Ten"]

        def has_data(dt: date) -> bool:
            self.count_probe()
            return check_exists(channel_id, dt)

        def on_probing(dt: date):
            logger.debug(f"Probing {dt} for channel {title!r}")

        def on_valid(dt: date):
            logger.info(f"Valid {dt} for channel {title!r}")

        def on_invalid(dt: date):
            logger.warning(f"Invalid {dt} for channel {title!r}")

        def on_done(lower: date, upper: date):
            logger.info(f"Done for channel {title!r}: {lower} - {upper}")

        def task():
            out = find_bounds(
                self.known_good,
                has_data,
                on_probing=on_probing,
                on_valid=on_valid,
                on_invalid=on_invalid,
                on_done=on_done,
                extra_info={"channel_id": channel_id, "title": title},
            )
            return channel_id, out

        self.tasks.append(self.mp.submit(task))

    def wait_for_completion(self):
        for fut in as_completed(self.tasks):
            try:
                channel_id, (lower, upper) = fut.result()
            except Exception:
                logger.exception(f"Error in task! ({fut!r})")
                continue
            self.results[channel_id] = (lower, upper)

    def run(self):
        for channel_id in self.channels:
            self.find_ranges(channel_id)
        self.wait_for_completion()
        logger.info(f"--> Total probes: {self.total_probes} probes")


def main():
    logger.info("Starting EPG range finding...")
    st = time.perf_counter()
    channels = fetch_channels()["DSKenh"]
    logger.info(f"--> Total channels: {len(channels)}")
    finder = EPGRangeFinder(
        date(2026, 1, 1), {channel["Ma"]: channel for channel in channels}
    )
    finder.run()
    end = time.perf_counter()
    logger.info(f"--> Finished in {end - st:.2f} seconds")

    result = {
        "channels": channels,
        "ranges": {
            c: {"lower": l.isoformat(), "upper": u.isoformat()}
            for c, (l, u) in finder.results.items()
        },
    }
    today = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"epg_ranges_{today}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        import json

        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
