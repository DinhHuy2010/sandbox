from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

import anyio
import msgspec
from niquests import AsyncSession, HTTPError, Response, Timeout
from structlog.typing import FilteringBoundLogger

from jio.crawler.cache import Cache
from jio.crawler.config import Config, JobSpec, Work
from jio.crawler.models import AboutResponse, DataResponse
from jio.lib import JIO_SCHEDULE_URL

MAX_ATTEMPTS = 5


class CrawlerStats(msgspec.Struct):
    cache_hits: int
    workers_fresh_crawl_ok: int
    workers_fails: int
    http_total_requests: int
    http_total_transferred_bytes: int
    http_counts_by_status: dict[int, int] = msgspec.field(
        default_factory=lambda: defaultdict(int)
    )

    def record_response(self, resp: Response) -> None:
        self.http_total_requests += 1
        self.http_total_transferred_bytes += len(resp.content)
        self.http_counts_by_status[resp.status_code] += 1

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def summary(self) -> dict[str, Any]:
        return {
            "cache_hits": self.cache_hits,
            "workers_fresh_crawl_ok": self.workers_fresh_crawl_ok,
            "workers_fails": self.workers_fails,
            "http_total_requests": self.http_total_requests,
            "http_total_transferred_bytes": self.http_total_transferred_bytes,
            "http_counts_by_status": dict(self.http_counts_by_status),
        }


class Crawler:
    def __init__(self, config: Config, logger: FilteringBoundLogger):
        self.config = config
        self.logger = logger.bind(name="jio/crawler")
        self.limiter = anyio.Semaphore(500)
        self.session = AsyncSession()
        self.cache = Cache(config, logger.bind(name="jio/crawler/cache"))
        self.stats = CrawlerStats(0, 0, 0, 0, 0)

    async def ensure(self) -> None:
        await self.config.ensure()

    async def _report_progress(self) -> None:
        while True:
            await anyio.sleep(10)
            await self._report_progress_single()

    async def _report_progress_single(self):
        await self.logger.ainfo("Crawl progress", **self.stats.summary())

    async def _crawl(
        self, channel_id: int, date_requested: date, worker_log: FilteringBoundLogger
    ) -> DataResponse:
        offset = (date_requested - datetime.now(UTC).date()).days
        if offset > 0:
            raise ValueError("Date cannot be in the future.")
        async with self.limiter:
            response = await self.session.get(
                JIO_SCHEDULE_URL.format(id=channel_id, offset=offset)
            )
        self.stats.record_response(response)
        response.raise_for_status()  # Raise an error for bad responses
        await worker_log.adebug(
            "Data pull from API successfully", status_code=response.status_code
        )
        data = response.json()
        return DataResponse(
            raw_data=data,
            about=AboutResponse(
                http_status_code=response.status_code,
                http_url=str(response.url),
                http_response_headers=dict(response.headers),
                channel_id=channel_id,
                date_requested=date_requested,
            ),
            last_crawl=datetime.now(UTC),
        )

    async def _worker(self, work: Work) -> None:
        worker_log = self.logger.bind(
            channel_id=work[0], date_requested=work[1].isoformat()
        )
        if self.cache.contains(work[0], work[1]):
            await worker_log.adebug("Cache hit, skipping crawl")
            self.stats.record_cache_hit()
            return
        await worker_log.adebug("Worker started")
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                dr = await self._crawl(work[0], work[1], worker_log)
                await self.cache.add(dr)
                self.stats.workers_fresh_crawl_ok += 1
                await worker_log.adebug("Worker finished successfully")
                return
            except HTTPError as e:
                if e.response.status_code == 404:
                    await worker_log.awarning(
                        "Worker failed with 404, skipping!",
                        attempt=attempt,
                        max_attempts=MAX_ATTEMPTS,
                    )
                    self.stats.workers_fails += 1
                    return
                elif e.response.status_code in {429, 500, 502, 503, 504}:
                    await worker_log.awarning(
                        f"Worker failed with {e.response.status_code}, retrying!",
                        attempt=attempt,
                        max_attempts=MAX_ATTEMPTS,
                    )
                    await anyio.sleep(0.5 * (2**attempt))  # Backoff before retrying
            except Timeout:
                await worker_log.awarning(
                    "Worker timed out, retrying!",
                    attempt=attempt,
                    max_attempts=MAX_ATTEMPTS,
                )
                await anyio.sleep(0.5 * (2**attempt))  # Backoff before retrying
            except Exception:
                await worker_log.aexception(
                    "Worker failed, retrying!",
                    attempt=attempt,
                    max_attempts=MAX_ATTEMPTS,
                )
                await anyio.sleep(0.5 * (2**attempt))  # Backoff before retrying
        await worker_log.aerror(
            "Worker failed after max attempts", max_attempts=MAX_ATTEMPTS
        )
        self.stats.workers_fails += 1

    async def crawl(self, jobspec: JobSpec) -> None:
        send_stream, receive_stream = anyio.create_memory_object_stream[Work](500)

        async def worker(receive_stream: anyio.abc.ObjectReceiveStream[Work]):
            async with receive_stream:
                async for work in receive_stream:
                    await self._worker(work=work)

        async def sender(send_stream: anyio.abc.ObjectSendStream[Work]):
            async with send_stream:
                for channel_id, date in jobspec.generate_jobs():
                    await send_stream.send((channel_id, date))

        await self.ensure()
        await self.cache.ensure()
        await self.logger.ainfo("Starting crawl!")
        async with anyio.create_task_group() as progess_tg:
            progess_tg.start_soon(self._report_progress)
            try:
                async with anyio.create_task_group() as crawl_tg:
                    crawl_tg.start_soon(sender, send_stream)
                    for _ in range(self.config.max_workers):
                        crawl_tg.start_soon(worker, receive_stream.clone())
                    await receive_stream.aclose()
            finally:
                progess_tg.cancel_scope.cancel()
        await self._report_progress_single()
        await self.logger.ainfo("Crawl finished!")
