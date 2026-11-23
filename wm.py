import datetime
import re
import statistics
import time
from dataclasses import dataclass
from datetime import date
from typing import cast

import htmllistparse

URL = "https://dumps.wikimedia.your.org/other/mediawiki_content_history/"
DUMP_DATE = "2026-11-01"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"}

# Standard range pattern
STANDARD_PATTERN = re.compile(
    r"^(?P<wiki_id>[a-z0-9]+)-(?P<date>\d{4}-\d{2}-\d{2})-p(?P<start_page>\d+)p(?P<end_page>\d+)\.xml\.bz2$"
)

# Split revision pattern
SPLIT_PATTERN = re.compile(
    r"^(?P<wiki_id>[a-z0-9]+)-(?P<date>\d{4}-\d{2}-\d{2})-p(?P<page_id>\d+)r(?P<start_rev>\d+)r(?P<end_rev>\d+)\.xml\.bz2$"
)


@dataclass
class DumpFile:
    name: str
    size: int
    modified: datetime
    wiki: str
    publication_date: date
    page_id_start: int
    page_id_end: int

    @classmethod
    def new(cls, name: str, size: int, modified: time.struct_time) -> "DumpFile":
        m = STANDARD_PATTERN.match(name)
        if not m:
            raise ValueError(f"Invalid filename: {name}")
        wiki_id = m.group("wiki_id")
        date_str = m.group("date")
        start_page = int(m.group("start_page"))
        end_page = int(m.group("end_page"))
        publication_date = date.fromisoformat(date_str)
        return cls(
            name=name,
            size=size,
            modified=datetime.datetime.fromtimestamp(time.mktime(modified)),
            wiki=wiki_id,
            publication_date=publication_date,
            page_id_start=start_page,
            page_id_end=end_page,
        )

    @property
    def total_pages(self) -> int:
        """Calculate the total number of pages in the dump file, inclusive."""
        return self.page_id_end - self.page_id_start + 1


@dataclass
class DumpFileSinglePageRevisions:
    name: str
    size: int
    modified: datetime.datetime
    wiki: str
    publication_date: date
    page_id: int
    revision_id_start: int
    revision_id_end: int

    @classmethod
    def new(
        cls, name: str, size: int, modified: time.struct_time
    ) -> "DumpFileSinglePageRevisions":
        m = SPLIT_PATTERN.match(name)
        if not m:
            raise ValueError(f"Invalid filename: {name}")
        wiki_id = m.group("wiki_id")
        date_str = m.group("date")
        page_id = int(m.group("page_id"))
        start_rev = int(m.group("start_rev"))
        end_rev = int(m.group("end_rev"))
        publication_date = date.fromisoformat(date_str)
        return cls(
            name=name,
            size=size,
            modified=datetime.datetime.fromtimestamp(time.mktime(modified)),
            wiki=wiki_id,
            publication_date=publication_date,
            page_id=page_id,
            revision_id_start=start_rev,
            revision_id_end=end_rev,
        )


def ls(url: str) -> list[tuple[str, int, time.struct_time]]:
    """List files in a directory on the web."""
    _, out = htmllistparse.fetch_listing(url, headers=HEADERS)
    return [
        (entry.name, entry.size, entry.modified)
        for entry in cast(list[htmllistparse.FileEntry], out)
    ]


def new(
    name: str, size: int, modified: time.struct_time
) -> DumpFile | DumpFileSinglePageRevisions:
    """Create a new DumpFile or DumpFileSinglePageRevisions object based on the filename."""
    if STANDARD_PATTERN.match(name):
        return DumpFile.new(name, size, modified)
    elif SPLIT_PATTERN.match(name):
        return DumpFileSinglePageRevisions.new(name, size, modified)
    else:
        raise ValueError(f"Invalid filename: {name}")


def bytes_to_human_readable(num_bytes: int) -> str:
    """Convert bytes to a human-readable format."""
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PiB"


wiki = "wikidatawiki"
base = f"{URL}{wiki}/{DUMP_DATE}/xml/bzip2/"
total = []
for item in ls(base):
    name, size, modified = item
    try:
        dump_file = new(name, size, modified)
        # print(dump_file)
    except ValueError as e:
        print(f"Skipping file {name}: {e}")
    else:
        total.append(dump_file)


def select_files_from_pages(
    pages: list[int],
) -> list[DumpFile | DumpFileSinglePageRevisions]:
    """Select files that contain the specified page IDs."""
    selected = []
    for f in total:
        if isinstance(f, DumpFile):
            if any(f.page_id_start <= page <= f.page_id_end for page in pages):
                selected.append(f)
        elif isinstance(f, DumpFileSinglePageRevisions) and f.page_id in pages:
            selected.append(f)
    return selected


def count_covered_page_ids(
    files: list[DumpFile | DumpFileSinglePageRevisions],
) -> int:
    """Count distinct page IDs covered by filename intervals.

    This does NOT count actual pages contained in the XML.
    """
    ranges = []

    for f in files:
        if isinstance(f, DumpFile):
            ranges.append((f.page_id_start, f.page_id_end))
        else:
            ranges.append((f.page_id, f.page_id))

    ranges.sort()

    total_count = 0
    start = end = None

    for left, right in ranges:
        if start is None:
            start, end = left, right
        elif left <= end + 1:
            end = max(end, right)
        else:
            total_count += end - start + 1
            start, end = left, right

    if start is not None:
        total_count += end - start + 1

    return total_count


print("--> Total files:", len(total))
total_size = sum(f.size for f in total)
average_size = statistics.mean(f.size for f in total) if total else 0
print(
    f"--> Total size: {total_size} bytes ({bytes_to_human_readable(total_size)}), average size: {average_size:.2f} bytes ({bytes_to_human_readable(average_size)})"
)
print(f"--> Total pages covered: {count_covered_page_ids(total)} pages")
