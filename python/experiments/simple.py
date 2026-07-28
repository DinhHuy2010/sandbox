from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import asynccontextmanager
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

import anyio
import logfire
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi import Path as FastAPIPath
from fastapi.responses import FileResponse, RedirectResponse
from httpx import AsyncClient, HTTPStatusError
from packaging.utils import parse_sdist_filename, parse_wheel_filename
from pydantic import BaseModel, Field
from simple_repository import SimpleRepository
from simple_repository.components.core import RepositoryContainer
from simple_repository.components.http_cached import (
    CachedHttpRepository as HttpRepository,
)
from simple_repository.content_negotiation import select_response_format
from simple_repository.errors import UnsupportedSerialization
from simple_repository.model import HttpResource, RequestContext
from simple_repository.serializer import serialize
from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


CACHE_ROOT = Path(os.getenv("SIMPLE_CACHE_ROOT", "./temp/mirrored_resources")).resolve()
REPOSITORY_CACHE_ROOT = Path(
    os.getenv("SIMPLE_REPOSITORY_CACHE_ROOT", "./.cache/simple-repository")
).resolve()
UPSTREAM_SIMPLE_URL = os.getenv("UPSTREAM_SIMPLE_URL", "https://pypi.org/simple/")
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://localhost:8000")
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def get_logfire_send_to_logfire() -> bool | str:
    value = os.getenv("LOGFIRE_SEND_TO_LOGFIRE")
    if value is None:
        return "if-token-present"

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", "local"}:
        return False
    return value


logfire.configure(
    service_name="simple-pypi-cache",
    send_to_logfire=get_logfire_send_to_logfire(),
)


class CacheMetadata(BaseModel):
    source_url: str
    cache_key: str
    filename: str
    size_bytes: int = Field(ge=0)
    etag: str | None = None
    last_modified: str | None = None
    content_type: str | None = None


class LocalRepositoryContainer(RepositoryContainer):
    def __init__(self, source: SimpleRepository):
        super().__init__(source)

    async def get_project_page(
        self, project_name: str, *, request_context: RequestContext | None = None
    ):
        with logfire.span("load project page", project_name=project_name):
            page = await self.source.get_project_page(project_name)
        return replace(
            page,
            files=[
                replace(file, url=f"{LOCAL_BASE_URL}/files/{file.filename}")
                if file.url
                else file
                for file in page.files
            ],
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    REPOSITORY_CACHE_ROOT.mkdir(parents=True, exist_ok=True)

    async with AsyncClient(
        follow_redirects=True,
        http2=True,
        timeout=60.0,
        headers={"User-Agent": "simple-pypi-cache/1.0"},
    ) as client:
        app.state.http_client = client
        logfire.instrument_httpx(client)
        logfire.info(
            "simple cache started",
            cache_root=str(CACHE_ROOT),
            repository_cache_root=str(REPOSITORY_CACHE_ROOT),
            upstream_simple_url=UPSTREAM_SIMPLE_URL,
        )
        yield
        logfire.info("simple cache stopped")


app = FastAPI(lifespan=lifespan)
logfire.instrument_fastapi(app)

_cache_locks: dict[Path, anyio.Lock] = {}


def safe_filename(filename: str) -> str:
    cleaned = SAFE_FILENAME_RE.sub("_", filename).strip("._")
    return cleaned or "resource"


def cache_key_for_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]


def get_local_path_for_resource(resource: HttpResource) -> Path:
    parsed_path = Path(urlparse(resource.url).path)
    filename = safe_filename(parsed_path.name or "resource")
    return CACHE_ROOT / f"{cache_key_for_url(resource.url)}-{filename}"


def get_metadata_path_for_resource(resource: HttpResource) -> Path:
    return get_local_path_for_resource(resource).with_suffix(
        get_local_path_for_resource(resource).suffix + ".json"
    )


def get_cache_lock(path: Path) -> anyio.Lock:
    lock = _cache_locks.get(path)
    if lock is None:
        lock = anyio.Lock()
        _cache_locks[path] = lock
    return lock


async def resource_cached(resource: HttpResource) -> bool:
    local_path = get_local_path_for_resource(resource)
    try:
        stat = await anyio.to_thread.run_sync(local_path.stat)
    except FileNotFoundError:
        logfire.info("cache miss", url=resource.url, path=str(local_path))
        return False

    cached = stat.st_size > 0
    logfire.info(
        "cache hit" if cached else "cache entry unusable",
        url=resource.url,
        path=str(local_path),
        size_bytes=stat.st_size,
    )
    return cached


async def write_cache_metadata(
    resource: HttpResource,
    response_headers: dict[str, str],
    size_bytes: int,
) -> None:
    metadata = CacheMetadata(
        source_url=resource.url,
        cache_key=cache_key_for_url(resource.url),
        filename=get_local_path_for_resource(resource).name,
        size_bytes=size_bytes,
        etag=response_headers.get("etag"),
        last_modified=response_headers.get("last-modified"),
        content_type=response_headers.get("content-type"),
    )
    metadata_path = get_metadata_path_for_resource(resource)
    await anyio.Path(metadata_path).write_text(
        json.dumps(metadata.model_dump(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


async def download_resource(resource: HttpResource, target_path: Path) -> None:
    client: AsyncClient = app.state.http_client
    temporary_path = target_path.with_name(f".{target_path.name}.download")
    bytes_written = 0

    with logfire.span("download resource", url=resource.url, path=str(target_path)):
        try:
            async with client.stream("GET", resource.url) as response:
                response.raise_for_status()
                async with await anyio.open_file(temporary_path, "wb") as file:
                    async for chunk in response.aiter_bytes(DOWNLOAD_CHUNK_SIZE):
                        bytes_written += len(chunk)
                        await file.write(chunk)

                await anyio.Path(temporary_path).replace(target_path)
                await write_cache_metadata(
                    resource,
                    dict(response.headers),
                    bytes_written,
                )
        except Exception:
            with anyio.CancelScope(shield=True):
                try:
                    await anyio.Path(temporary_path).unlink(missing_ok=True)
                except Exception:
                    logfire.exception(
                        "failed to remove temporary cache file",
                        path=str(temporary_path),
                    )
            raise

    logfire.info(
        "resource cached",
        url=resource.url,
        path=str(target_path),
        size_bytes=bytes_written,
    )


async def cache_resource_to_disk(resource: HttpResource) -> Path:
    local_path = get_local_path_for_resource(resource)
    lock = get_cache_lock(local_path)

    async with lock:
        if await resource_cached(resource):
            return local_path

        try:
            await download_resource(resource, local_path)
        except HTTPStatusError as exc:
            logfire.warning(
                "upstream download failed",
                url=resource.url,
                status_code=exc.response.status_code,
            )
            raise
        except Exception:
            logfire.exception("cache download failed", url=resource.url)
            raise

    return local_path


async def warm_cache(resource: HttpResource) -> None:
    try:
        await cache_resource_to_disk(resource)
    except Exception:
        logfire.exception("background cache warm failed", url=resource.url)


@lru_cache(maxsize=1)
def get_repository() -> SimpleRepository:
    return LocalRepositoryContainer(
        HttpRepository(UPSTREAM_SIMPLE_URL, REPOSITORY_CACHE_ROOT)
    )


@app.get("/simple/", response_class=Response, summary="Get project list")
async def project_list(
    repository: Annotated[SimpleRepository, Depends(get_repository)], request: Request
) -> Response:
    content_type = request.headers.get("Accept", "")
    response_format = select_response_format(content_type)

    with logfire.span("serve project list", response_format=response_format.value):
        project_names = await repository.get_project_list()
        content = serialize(project_names, response_format)

    return Response(content=content, media_type=response_format.value)


@app.get(
    "/simple/{project_name}/", response_class=Response, summary="Get project details"
)
async def project_detail(
    project_name: Annotated[
        str,
        FastAPIPath(
            ...,
            description="The name of the project to retrieve details for",
            examples=["example_project", "another_project"],
        ),
    ],
    repository: Annotated[SimpleRepository, Depends(get_repository)],
    request: Request,
) -> Response:
    content_type = request.headers.get("Accept", "")
    response_format = select_response_format(content_type)

    with logfire.span(
        "serve project detail",
        project_name=project_name,
        response_format=response_format.value,
    ):
        project_details = await repository.get_project_page(project_name)
        content = serialize(project_details, response_format)

    return Response(content=content, media_type=response_format.value)


@app.get("/files/{file}", response_class=Response, summary="Serve project files")
async def serve_resource(
    file: Annotated[
        str,
        FastAPIPath(
            ...,
            description="The filename to serve from the repository's resources",
            examples=[
                "example_project-1.0.0-py3-none-any.whl",
                "example_project-1.0.0.tar.gz",
            ],
        ),
    ],
    repository: Annotated[SimpleRepository, Depends(get_repository)],
    bg: BackgroundTasks,
) -> Response:
    project_name = get_project_name_from_distribution_filename(file)
    resource = await repository.get_resource(project_name, file)

    if not isinstance(resource, HttpResource):
        logfire.error("repository returned non-http resource", file=file)
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    local_path = get_local_path_for_resource(resource)
    with logfire.span(
        "serve resource",
        file=file,
        project_name=str(project_name),
        url=resource.url,
        cache_path=str(local_path),
    ):
        if await resource_cached(resource):
            return FileResponse(local_path, status_code=200)

        bg.add_task(warm_cache, resource)
        logfire.info("redirecting while cache warms", url=resource.url, file=file)
        return RedirectResponse(resource.url, status_code=302)


def get_project_name_from_distribution_filename(filename: str):
    distribution_filename = filename.removesuffix(".metadata")
    try:
        return parse_wheel_filename(distribution_filename)[0]
    except Exception:
        try:
            return parse_sdist_filename(distribution_filename)[0]
        except Exception:
            logfire.warning("could not parse distribution filename", file=filename)
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Resource not found"
            ) from None


@app.exception_handler(UnsupportedSerialization)
async def unsupported_serialization_exception_handler(
    request: Request, exc: UnsupportedSerialization
):
    logfire.warning(
        "unsupported serialization requested",
        accept=request.headers.get("Accept", ""),
        path=request.url.path,
    )
    raise HTTPException(status_code=406, detail=str(exc))
