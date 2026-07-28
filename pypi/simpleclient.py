from typing import Any, Iterable, cast

import httpx
import json_stream
import json_stream.httpx
from hishel import CacheOptions, SpecificationPolicy, SyncSqliteStorage
from hishel.httpx import SyncCacheTransport
from lxml import etree

from python.lib.breader import BReader
from package_filenames import parse_filename
from pep691_models import (
    File,
    Project,
    ProjectItem,
    ProjectMeta,
    ProjectStatus,
    StatusData,
)

# from pypi_simple

#: :mailheader:`Accept` header value for accepting only the JSON serialization
ACCEPT_JSON_ONLY = "application/vnd.pypi.simple.v1+json"

#: :mailheader:`Accept` header value for accepting only the HTML serialization
ACCEPT_HTML_ONLY = ", ".join(
    [
        "application/vnd.pypi.simple.v1+html",
        "text/html;q=0.01",
    ]
)

#: :mailheader:`Accept` header value for accepting either the HTML or JSON
#: serialization with a preference for JSON
ACCEPT_JSON_PREFERRED = ", ".join(
    [
        "application/vnd.pypi.simple.v1+json",
        "application/vnd.pypi.simple.v1+html;q=0.5",
        "text/html;q=0.01",
    ]
)

#: :mailheader:`Accept` header value for accepting either the HTML or JSON
#: serialization with a preference for HTML
ACCEPT_HTML_PREFERRED = ", ".join(
    [
        "application/vnd.pypi.simple.v1+html",
        "text/html;q=0.5",
        "application/vnd.pypi.simple.v1+json;q=0.1",
    ]
)


def stream_project_names(client: httpx.Client, endpoint: str) -> Iterable[ProjectItem]:
    with client.stream("GET", endpoint) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        print(content_type)
        print(response.extensions)
        if content_type == "application/vnd.pypi.simple.v1+json":
            data = cast(Any, json_stream.httpx.load(response))  # type: ignore
            for item in data["projects"]:
                yield ProjectItem.model_validate(
                    json_stream.to_standard_types(item)  # type: ignore
                )
        elif content_type in {"application/vnd.pypi.simple.v1+html", "text/html"}:
            f = BReader(response.iter_bytes())
            for _, elem in etree.iterparse(f, events=["end"], tag="a", html=True):
                assert elem.text is not None
                yield ProjectItem(name=elem.text)
                elem.clear()
        else:
            raise ValueError(f"Unsupported Content-Type: {content_type}")


def parse_fragment_hash(fragment: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    hash_algo, hash_value = fragment.split("=", 1)
    hashes[hash_algo] = hash_value
    return hashes


def to_bool(value: str) -> bool:
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    else:
        raise ValueError(f"Invalid boolean value: {value}")


def infer_versions_from_files(files: list[File]) -> list[str]:
    versions: set[str] = set()
    for file in files:
        _, version, _ = parse_filename(file.filename)
        versions.add(version)
    return sorted(versions)


def get_project_info(client: httpx.Client, endpoint: str, project_name: str) -> Project:
    response = client.get(f"{endpoint}/{project_name}")
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if content_type == "application/vnd.pypi.simple.v1+json":
        data = response.json()
        return Project.model_validate(data)
    elif content_type in {"application/vnd.pypi.simple.v1+html", "text/html"}:
        return parse_html_response_to_info(project_name, response)

    else:
        raise ValueError(f"Unsupported Content-Type: {content_type}")


def parse_html_response_to_info(project_name: str, response: httpx.Response) -> Project:
    f = BReader(response.iter_bytes())
    files: list[File] = []
    project_status: ProjectStatus | None = None
    project_status_reason: str | None = None
    repository_version: str | None = None
    for _, elem in etree.iterparse(f, events=["end"], html=True):
        if elem.tag == "a":
            filename = elem.text
            href = elem.get("href")
            assert filename is not None
            assert href is not None
            url = httpx.URL(href)
            frag = url.fragment
            hashes = parse_fragment_hash(frag) if frag else {}
            yanked = elem.get("data-yanked")
            core_metadata = elem.get("data-core-metadata") or elem.get(
                "data-dist-info-metadata"
            )
            gpg_sig = elem.get("data-gpg-sig")
            url_no_frag = url.copy_with(fragment=None)
            files.append(
                File(
                    filename=filename,
                    url=str(url_no_frag),
                    hashes=hashes,
                    size=None,
                    upload_time=None,
                    yanked=yanked or False,
                    requires_python=elem.get("data-requires-python"),
                    provenance=elem.get("data-provenance"),  # type: ignore
                    core_metadata=parse_fragment_hash(core_metadata)
                    if core_metadata is not None
                    else None,
                    gpg_sig=to_bool(gpg_sig) if gpg_sig is not None else None,
                )
            )
        elif elem.tag == "meta":
            name = elem.get("name")
            if name == "pypi:project-status":
                content = elem.get("content")
                if content is not None:
                    project_status = ProjectStatus(content)
            elif name == "pypi:project-status-reason":
                content = elem.get("content")
                if content is not None:
                    project_status_reason = content
            elif name == "pypi:repository-version":
                content = elem.get("content")
                if content is not None:
                    repository_version = content

        elem.clear()

    return Project(
        name=project_name,
        files=files,
        project_status=StatusData(status=project_status, reason=project_status_reason),
        meta=ProjectMeta.model_validate(
            {
                "api-version": repository_version,
                "tracks": [],
                "_last-serial": response.headers.get("X-PyPI-Last-Serial"),
            }
        ),
        versions=infer_versions_from_files(files),
    )


transport = SyncCacheTransport(
    httpx.HTTPTransport(),
    storage=SyncSqliteStorage(database_path="pypi_simple_http_cache.db"),
    policy=SpecificationPolicy(
        CacheOptions(shared=False),
    ),
)

client = httpx.Client(
    transport=transport,
    headers={"Accept": ACCEPT_JSON_PREFERRED},
    follow_redirects=True,
)
info = get_project_info(client, "https://pypi.org/simple/", "uv")
print(info)
