import importlib
import importlib.metadata
from zipfile import Path, ZipFile

from hishel import CacheOptions, SpecificationPolicy, SyncSqliteStorage
from hishel.httpx import SyncCacheTransport
from httpx import Client, HTTPTransport, Request, Response

from python.lib.rangeresp import open_http


def print_request_as_http_message(request: Request):
    print(
        f"{request.method} {request.url.path} {request.extensions.get('http_version', 'HTTP/1.1')}"
    )
    for name, value in request.headers.items():
        print(f"{name}: {value}")
    print()


def print_response_as_http_message(response: Response):
    print(f"{response.http_version} {response.status_code} {response.reason_phrase}")
    for name, value in response.headers.items():
        print(f"{name}: {value}")
    print()
    print("# response.extensions:")
    for name, value in response.extensions.items():
        print(f"{name}: {value}")


cached_transport = SyncCacheTransport(
    HTTPTransport(),
    SyncSqliteStorage(default_ttl=3600),
    SpecificationPolicy(CacheOptions(allow_stale=True)),
)

# url = "https://files.pythonhosted.org/packages/13/16/42e5915ebe4868caa6bac83a8ed59db57f12e9a61b7d749d584776ed53d5/torch-2.11.0-cp312-cp312-manylinux_2_28_aarch64.whl"
url = "https://files.pythonhosted.org/packages/c4/a8/3a61a721472959ab0ce865ef05d10b0d6bfe27ce8801c99f33d4fa996e65/pandas-3.0.2-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl"

client = Client(
    headers={"User-Agent": "curl/7.64.1"},
    follow_redirects=True,
    # event_hooks={
    #     "request": [print_request_as_http_message],
    #     "response": [print_response_as_http_message],
    # },
    transport=cached_transport,
)
with open_http(url, client=client, verbose=False, flexible_range=False) as f:
    zf = ZipFile(f)
    zp = Path(zf)
    d = next(zp.glob("*.dist-info"))
    dist = importlib.metadata.PathDistribution(d)
    print(dist.metadata["Description"])
    # with open("torch-ziplisting.txt", "w") as out:
    #     zf.printdir(out)
