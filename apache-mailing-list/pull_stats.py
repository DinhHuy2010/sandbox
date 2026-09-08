import json
from collections import Counter

import anyio
import niquests

session = niquests.AsyncSession()
SEM = anyio.Semaphore(20)

APACHE_LISTS_BASE_URL = "https://lists.apache.org"


async def get_stats_api(list_addr):
    url = f"{APACHE_LISTS_BASE_URL}/api/stats.lua"
    ls, domain = list_addr.split("@")
    params = {"list": ls, "domain": domain}
    async with SEM:
        response = await session.get(url, params=params)
        return response.json()


async def main():
    async with await anyio.open_file("lists.json", "r") as f:
        lists = json.loads(await f.read())
    addresses = [address for v in lists.values() for address in v]
    for a in addresses:
        list_, domain = a.split("@")
        api_url = (
            f"{APACHE_LISTS_BASE_URL}/api/stats.lua?list={list_}&domain={domain}&quick"
        )
        print(f"{api_url}")
        print(f"   dir=stats/{domain}")
        print(f"   out={list_}.json")
        print()
    # async def go(address):
    #     print(f"Getting stats for {address}")
    #     resp = await get_stats_api(address)
    #     active_months = Counter(resp["active_months"])
    #     total_messages = sum(active_months.values())
    #     print(
    #         f"{address}: {total_messages} total messages in {len(active_months)} months"
    #     )

    # async with anyio.create_task_group() as tg:
    #     for address in addresses:
    #         tg.start_soon(go, address)
    # address = "dev@httpd.apache.org"
    # o = await get_stats_api(address)


if __name__ == "__main__":
    anyio.run(main, backend_options={"use_uvloop": True})
