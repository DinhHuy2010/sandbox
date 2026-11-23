from datetime import date

import anyio
import typer
from niquests import HTTPError
from structlog import get_logger
from structlog.stdlib import BoundLogger

from vtvcab_data.lib import pull_listing

log: BoundLogger = get_logger(name="vtvcab_data/tools/discover_ranges")


async def find_max_date(start=date(2022, 12, 31)):
    llog = log.bind(start=start.isoformat())
    lo = start.toordinal()
    step = 1

    async def check(day: date) -> bool:
        try:
            response = await pull_listing(day)
        except HTTPError as e:
            if e.response.status_code == 429:
                raise RuntimeError("Rate limited")

            if e.response.status_code == 500:
                await llog.adebug("Out of range", candidate=day.isoformat())
                return False  # Assumption: outside supported range
            raise
        else:
            await llog.adebug("Found accepted date", candidate=day.isoformat())
            return True

    await llog.ainfo("Starting search for max date", start=start.isoformat())

    # Phase 1: Exponential search
    while True:
        hi = min(lo + step, date.max.toordinal())

        await llog.adebug(
            "Attempting to check date", candidate=date.fromordinal(hi).isoformat()
        )
        if not await check(date.fromordinal(hi)):
            await llog.adebug(
                "Found upper bound", candidate=date.fromordinal(hi).isoformat()
            )
            break

        lo = hi
        step *= 2

        if lo == date.max.toordinal():
            return date.max

    # Phase 2: Binary search
    while hi - lo > 1:
        mid = (lo + hi) // 2
        await llog.adebug(
            "Finding dates between",
            lo=date.fromordinal(lo).isoformat(),
            hi=date.fromordinal(hi).isoformat(),
        )
        if await check(date.fromordinal(mid)):
            lo = mid
        else:
            hi = mid

    await llog.ainfo("Found max date", max_date=date.fromordinal(lo).isoformat())

    return date.fromordinal(lo)


def main(
    lower_bound: str = typer.Argument(
        "2022-12-31", help="The lower bound date in YYYY-MM-DD format"
    ),
) -> None:
    """Discover the maximum supported date starting from the given lower bound."""
    start_date = date.fromisoformat(lower_bound)
    max_date = anyio.run(find_max_date, start_date)
    typer.echo(f"Maximum supported date: {max_date.isoformat()}")


if __name__ == "__main__":
    typer.run(main)
