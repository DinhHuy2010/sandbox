import argparse
import datetime
import fileinput
import re
import sys
from contextlib import redirect_stdout
from sys import stderr
from typing import IO

import orjson

CHECKSUMS_REGEX_SECTION = re.compile(
    r"\[Checksums (.+)\]", re.MULTILINE | re.IGNORECASE
)
parser = argparse.ArgumentParser(
    description="Read and process a Fedora mirror file list",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "files", nargs="*", help="Input files to read (default: stdin)", default=["-"]
)
parser.add_argument(
    "--stats-on-nentries",
    type=int,
    default=0,
    help="Print stats after reading this many entries (default: 0, i.e. never)",
)
parser.add_argument(
    "--version",
    action="version",
    version="%(prog)s 0.1",
    help="Print version and exit",
)
parser.add_argument(
    "--dump",
    action="store_true",
    help="Dump the entries to stdout (default: False)",
)
parser.add_argument(
    "--slient",
    action="store_true",
    help="Suppress debug output (default: False)",
)


def extract_and_stream(f: IO[str], stats_on_nentries: int = 0):
    in_files_section = False
    in_version_section = False
    # checksum_section_type = None
    fit = iter(f)
    yield {"event": "start"}
    stats = {
        "entries.total": 0,
        "entries.files": 0,
        "entries.dirs": 0,
        "entries.total_size": 0,
    }
    for line in fit:
        line = line.strip()
        if not line:
            continue
        if line == "[Files]":
            in_files_section = True
            continue
        elif line == "[End]":
            break
        elif line == "[Version]":
            in_version_section = True
            continue
        elif CHECKSUMS_REGEX_SECTION.search(line):
            in_files_section = False
            continue
        if in_version_section:
            version = int(line)
            yield {"event": "version", "version": version}
            in_version_section = False
        if in_files_section:
            try:
                timestamp, entry_type, size, relative_path = line.split("\t")
            except ValueError:
                continue
            timestamp = datetime.datetime.fromtimestamp(int(timestamp), datetime.UTC)
            size = int(size)
            yield {
                "event": "entry",
                "timestamp": timestamp,
                "type": entry_type,
                "size": size,
                "path": relative_path,
            }
            stats["entries.total"] += 1
            if entry_type == "f":
                stats["entries.total_size"] += size
                stats["entries.files"] += 1
            elif entry_type == "d":
                stats["entries.dirs"] += 1
        if stats_on_nentries and stats["entries.total"] % stats_on_nentries == 0:
            yield {"event": "stats", "stats": stats.copy()}
    yield {"event": "stats", "stats": stats.copy()}
    yield {"event": "done"}


def numfmt(
    num: int, units: str | list[str] | None = None, div: int | None = None
) -> str:
    if isinstance(units, str):
        if units == "binary":
            units = ["", "K", "M", "G", "T"]
            div = 1024
        elif units == "decimal":
            units = ["", "k", "M", "B", "T"]
            div = 1000
    elif units is None:
        units = ["", "K", "M", "G", "T"]
        div = 1024
    else:
        if div is None:
            div = 1024
    for unit in units[:-1]:
        if abs(num) < div:
            return f"{num:3.1f}{unit}"
        num /= div
    return f"{num:.1f}{units[-1]}"


SLIENT = False


def print_debug(*msg: str):
    if not SLIENT:
        with redirect_stdout(stderr):
            print(*msg)


def print_report(n_entries: int, total_size: int):
    print_debug(
        "Stats after reading",
        numfmt(n_entries, units="decimal"),
        "entries:",
        "Total size:",
        numfmt(total_size) + "iB",
        # end="\r",
    )


def main():
    global SLIENT
    args = parser.parse_args()
    files = args.files
    dump = args.dump
    if args.slient:
        SLIENT = True
    with fileinput.FileInput(files=files, mode="r") as f:
        print_debug(f"Reading input from {f.filename() or 'stdin'!r}...")
        for event in extract_and_stream(f, stats_on_nentries=args.stats_on_nentries):
            if event["event"] == "entry":
                event.pop("event")
                if dump:
                    sys.stdout.buffer.write(orjson.dumps(event))
                    sys.stdout.buffer.write(b"\n")
            elif event["event"] == "stats":
                stats = event["stats"]
                print_report(stats["entries.total"], stats["entries.total_size"])


if __name__ == "__main__":
    main()
