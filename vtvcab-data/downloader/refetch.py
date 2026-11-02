import argparse
import json
from pathlib import Path
from secrets import token_hex

import anyio
import arrow
import niquests

parser = argparse.ArgumentParser(description="Refetch data from a given URL.")
parser.add_argument(
    "daterange",
    type=str,
    help="Date range for the data to be fetched, inclusive (e.g., '2021-01-01:2021-01-31').",
)


session = niquests.AsyncSession()
sem = anyio.Semaphore(10)  # Limit concurrent requests to 10

DATA_DIR = Path("out/raw").resolve()


async def request(date: arrow.Arrow):
    async with sem:
        url = f"https://apigateway.vtvcab.vn/mycab/api/v2/landing-page/broadcast_list?date={date.format('YYYY-MM-DD')}"
        response = await session.get(url)
        if response.status_code == 200:
            return response.content
        return None


def rename(old_name: str, new_name: str):
    old_path = DATA_DIR / old_name
    new_path = DATA_DIR / new_name
    if old_path.exists():
        old_path.rename(new_path)
        print(f"Renamed {old_name} to {new_name}")
    else:
        print(f"File {old_name} does not exist. Cannot rename.")


async def main(from_date, to_date):
    from_date = arrow.get(from_date)
    to_date = arrow.get(to_date)
    out = {}

    async def task(date):
        nonlocal out
        data = await request(date)
        if data is not None:
            out[date.format("YYYY-MM-DD")] = data

    print(
        f"Refetching data from {from_date.format('YYYY-MM-DD')} to {to_date.format('YYYY-MM-DD')}"
    )
    refreshed, missing = 0, 0
    tasks = []
    async with anyio.create_task_group() as task_group:
        for date in arrow.Arrow.range("day", from_date, to_date):
            tasks.append(task_group.start_soon(task, date))
    tasks.clear()
    for date in arrow.Arrow.range("day", from_date, to_date):
        if date.format("YYYY-MM-DD") in out:
            refreshed += 1
        else:
            missing += 1
    print(f"Refreshed: {refreshed}, Missing: {missing}")
    for date, data in out.items():
        if not data:
            continue
        filename = f"{date}.json"
        filepath = DATA_DIR / filename
        print(f"Writing data for {date} to {filepath}")
        rename(filename, f"{date}.json.{token_hex(4)}.bak")
        async with await anyio.open_file(filepath, "wb",) as f:
            await f.write(data)


if __name__ == "__main__":
    args = parser.parse_args()
    from_date, to_date = args.daterange.split(":")
    anyio.run(
        main,
        from_date,
        to_date,
        backend="asyncio",
        backend_options={"use_uvloop": True},
    )
