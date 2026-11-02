import argparse
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import anyio
import httpx

from downloader.main import Downloader, SCTVAdapter, Settings
from libsctv import CHANNELS_URL, EPG_URL, LOCAL_TZ


class SCTVFetcher(SCTVAdapter):
    async def discover_channels(self, client: httpx.AsyncClient) -> list[int]:
        resp = await client.post(
            CHANNELS_URL,
            json={},
            headers={
                "Content-Type": "application/json; charset=UTF-8",
            },
        )
        resp.raise_for_status()
        data = resp.json()["DSKenh"]
        return [x["Ma"] for x in data]

    async def fetch(self, client: httpx.AsyncClient, channel_id: int, day: date) -> Any:
        dt = datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_TZ)
        to_send = dt.astimezone(UTC).isoformat()
        resp = await client.post(
            EPG_URL,
            json={"maKenh": str(channel_id), "ngay": to_send},
        )
        resp.raise_for_status()
        return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    args = parser.parse_args()
    anyio.run(
        Downloader(Settings.load(args.config), SCTVFetcher()).run,
        backend_options={"use_uvloop": True},
    )


if __name__ == "__main__":
    main()
