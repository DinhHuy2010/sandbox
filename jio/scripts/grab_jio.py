from datetime import UTC, date, datetime, timedelta

import anyio
import msgspec
import niquests
import structlog

from jio.logging_infra import get_logger

URL = "https://jiotvapi.cdn.jio.com/apis/v1.3/getepg/get"

MAX_CONCURRENT_REQUESTS = 100
EARLIEST_ALLOWED = date(2000, 1, 1)


class EPGProbe:
    def __init__(
        self,
        client: niquests.AsyncSession,
        logger: structlog.typing.FilteringBoundLogger,
    ) -> None:
        self.client = client
        self.limiter = anyio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.today = datetime.now(UTC).date()
        self.log: structlog.typing.FilteringBoundLogger = logger

    async def check(self, channel_id: int, target: date) -> bool:
        log = self.log.bind(channel_id=channel_id, target=target)
        offset = (target - self.today).days

        for attempt in range(6):
            try:
                async with self.limiter:
                    response = await self.client.get(
                        URL,
                        params={
                            "channel_id": channel_id,
                            "offset": offset,
                        },
                    )

                if response.status_code == 429 or (500 <= response.status_code < 600):
                    raise niquests.HTTPError(
                        "Retryable HTTP status",
                        request=response.request,
                        response=response,
                    )
                if response.status_code == 404:
                    return False

                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict):
                    raise ValueError("Unexpected response structure")  # noqa: TRY004

                epg = data.get("epg")
                if not isinstance(epg, list):
                    raise ValueError("Missing or invalid epg field")  # noqa: TRY004

                return len(epg) > 0

            except (niquests.Timeout, niquests.HTTPError) as exc:
                if (
                    isinstance(exc, niquests.HTTPError)
                    and exc.response.status_code == 404
                ):
                    return False
                await log.aexception(
                    "Retry channel=%s offset=%s attempt=%s: %s",
                    channel_id,
                    offset,
                    attempt + 1,
                    exc,
                )
                await anyio.sleep(0.5 * (2**attempt))

        raise RuntimeError("Unreachable!")

    async def find_earliest(
        self,
        channel_id: int,
        minimum: date = EARLIEST_ALLOWED,
    ) -> date:
        log = self.log.bind(channel_id=channel_id, minimum=minimum)
        good = self.today

        if not await self.check(channel_id, good):
            raise ValueError(f"No EPG for channel {channel_id} today")

        step = 1

        # Phase 1: exponential search
        while True:
            candidate = max(
                minimum,
                good - timedelta(days=step),
            )

            if candidate == good:
                return good

            await log.adebug(
                "Performing exponential search",
                date=candidate,
            )

            if await self.check(channel_id, candidate):
                good = candidate
                if good == minimum:
                    return good
                step *= 2
            else:
                bad = candidate
                break

        # Phase 2: binary search
        while (good - bad).days > 1:
            middle = bad + (good - bad) // 2

            await log.adebug("Performing binary search", middle=middle)

            if await self.check(channel_id, middle):
                good = middle
            else:
                bad = middle

        return good


async def main(log: structlog.typing.FilteringBoundLogger):
    from jio.lib import pull_channels_list

    channel_ids = [x["channel_id"] for x in await pull_channels_list()]
    # channel_ids = [1, 2, 3, 4, 5]  # Replace with real IDs
    results = {}
    errors = {}

    async with niquests.AsyncSession() as client:
        probe = EPGProbe(client, log)
        await log.ainfo("Starting EPG probe", total_channels=len(channel_ids))

        async def worker(channel_id: int):
            try:
                earliest = await probe.find_earliest(channel_id)
                results[channel_id] = earliest
                await log.ainfo(
                    "FOUND channel=%s earliest=%s",
                    channel_id,
                    earliest,
                    channel_id=channel_id,
                    earliest=earliest,
                )
            except Exception as exc:
                errors[channel_id] = str(exc)
                await log.aexception(
                    "FAILED channel=%s",
                    channel_id,
                    exc,
                    channel_id=channel_id,
                )

        async with anyio.create_task_group() as tg:
            await log.ainfo("Launching workers for EPG probe", total_channels=len(channel_ids))
            for channel_id in channel_ids:
                tg.start_soon(worker, channel_id)
            await log.ainfo("All workers launched for EPG probe", total_channels=len(channel_ids))

    print("\nResults:")
    for channel_id, earliest in sorted(results.items()):
        print(f"{channel_id}: {earliest}")

    if errors:
        print("\nErrors:", errors)

    await log.ainfo("--> Dumping results to 'earliest_epg.json'...")

    async with await anyio.open_file("earliest_epg.json", "wb") as f:
        await f.write(msgspec.json.encode(results))


if __name__ == "__main__":
    with get_logger("jioprobe", logs_jsonl="logs/jioprobe.jsonl") as log:
        anyio.run(
            main,
            log,
            backend="asyncio",
            backend_options={"use_uvloop": True},
        )
