import csv
import io
from contextlib import redirect_stdout
from importlib.metadata import PathDistribution
from sys import stderr
from zipfile import Path, ZipFile

import httpx

from rangerespv2 import HTTPFile, LRUMapping


def print_http_request(request: httpx.Request):
    with redirect_stdout(stderr):
        print(
            f"{request.method} {request.url.path} {request.extensions.get('http_version', 'HTTP/1.1')}"
        )
        for name, value in request.headers.items():
            print(f"{name}: {value}")
        print()


def print_http_response(response: httpx.Response):
    with redirect_stdout(stderr):
        print(
            f"{response.http_version} {response.status_code} {response.reason_phrase}"
        )
        for name, value in response.headers.items():
            print(f"{name}: {value}")
        print()


def _test():
    # BELOW IS TEST CODE, NOT PART OF THE LIBRARY

    url = "https://files.pythonhosted.org/packages/47/e8/b98ca2d39b2e0e4730c0ee52537e488e7008025bc77ca89552ff91021f7c/torch-2.11.0-cp314-cp314-manylinux_2_28_x86_64.whl"
    # url = "https://github.com/CVEProject/cvelistV5/releases/download/cve_2026-04-08_1200Z/2026-04-08_all_CVEs_at_midnight.zip.zip"
    # url = "https://archive.org/download/BigBuckBunny_328/BigBuckBunny.avi"

    fp = HTTPFile(
        url,
        httpx.Client(
            follow_redirects=True,
            event_hooks={
                "request": [print_http_request],
                "response": [print_http_response],
            },
        ),
        cache=LRUMapping(max_size=1024),
        chunk_size=1024 * 1024,  # 1 MiB
    )
    with ZipFile(fp.buffered()) as zip_file:
        p = Path(zip_file)
        dist = PathDistribution(p)
        print(dist)


def _geonames_example():
    GEONAMES_COLUMNS = [
        "geonameid",
        "name",
        "asciiname",
        "alternatenames",
        "latitude",
        "longitude",
        "feature class",
        "feature code",
        "country code",
        "cc2",
        "admin1 code",
        "admin2 code",
        "admin3 code",
        "admin4 code",
        "population",
        "elevation",
        "dem",
        "timezone",
        "modification date",
    ]
    url = "https://download.geonames.org/export/dump/allCountries.zip"
    with HTTPFile(
        url,
        httpx.Client(
            follow_redirects=True,
            event_hooks={
                "request": [print_http_request],
                "response": [print_http_response],
            },
        ),
    ) as fp:
        with ZipFile(fp.buffered()) as zip_file:
            with zip_file.open("allCountries.txt") as f:
                tf = io.TextIOWrapper(f, encoding="utf-8")
                reader = csv.DictReader(tf, fieldnames=GEONAMES_COLUMNS, delimiter="\t")
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    print(row)


if __name__ == "__main__":
    _geonames_example()
