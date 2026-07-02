from collections.abc import Iterator
from compression import zstd
from dataclasses import dataclass
from json import loads
from pathlib import PurePosixPath
import struct
from typing import Any, BinaryIO


PATH = "./temp/nix-index-x86_64-linux.dat"
MAGIC = b"NIXI"
FORMAT_VERSION = 1


class FrcodeError(Exception):
    pass


class SharedOutOfRange(FrcodeError):
    def __init__(self, previous_len: int, shared_len: int):
        super().__init__(
            f"length of shared prefix must be >= 0 and <= {previous_len}, found {shared_len}"
        )
        self.previous_len = previous_len
        self.shared_len = shared_len


class SharedOverflow(FrcodeError):
    def __init__(self, shared_len: int, diff: int):
        super().__init__(
            f"length of shared prefix too big: cannot add {shared_len} to {diff}"
        )
        self.shared_len = shared_len
        self.diff = diff


class MissingNul(FrcodeError):
    pass


class MissingNewline(FrcodeError):
    pass


class MissingPrefixDifferential(FrcodeError):
    pass


class Decoder:
    def __init__(self, reader: BinaryIO):
        self.reader = reader
        self.last_path = b""
        self.shared_len = 0

    def _read_until_nul(self) -> bytes:
        out = bytearray()
        while True:
            b = self.reader.read(1)
            if b == b"":
                if out:
                    raise MissingNul("unexpected EOF before NUL")
                raise EOFError
            if b == b"\x00":
                return bytes(out)
            out.extend(b)

    def _read_diff(self) -> int:
        first = self.reader.read(1)
        if first == b"":
            raise MissingPrefixDifferential("missing shared prefix differential")
        if first != b"\x80":
            return int.from_bytes(first, byteorder="big", signed=True)

        rest = self.reader.read(2)
        if len(rest) != 2:
            raise MissingPrefixDifferential(
                "missing extended shared prefix differential"
            )
        return int.from_bytes(rest, byteorder="big", signed=True)

    def _read_until_newline(self) -> bytes:
        out = bytearray()
        while True:
            b = self.reader.read(1)
            if b == b"":
                raise MissingNewline("unexpected EOF before newline")
            if b == b"\n":
                return bytes(out)
            out.extend(b)

    def read_entry(self) -> tuple[bytes, bytes]:
        meta = self._read_until_nul()
        diff = self._read_diff()

        new_shared = self.shared_len + diff
        if new_shared < 0:
            raise SharedOutOfRange(
                previous_len=len(self.last_path), shared_len=new_shared
            )
        if new_shared > len(self.last_path):
            raise SharedOutOfRange(
                previous_len=len(self.last_path), shared_len=new_shared
            )

        suffix = self._read_until_newline()
        path = self.last_path[:new_shared] + suffix

        self.last_path = path
        self.shared_len = new_shared
        return meta, path

    def __iter__(self) -> Iterator[tuple[bytes, bytes]]:
        while True:
            try:
                yield self.read_entry()
            except EOFError:
                return


@dataclass
class RegularFileRecord:
    file: PurePosixPath
    size: int
    is_executable: bool


@dataclass
class DirectoryRecord:
    directory: PurePosixPath
    children: int


@dataclass
class SymlinkRecord:
    link: PurePosixPath
    target: str


@dataclass
class MetadataRecord:
    metadata: Any


@dataclass
class Record:
    metadata: MetadataRecord
    records: list[RegularFileRecord | DirectoryRecord | SymlinkRecord]


def decode_pair(
    metadata: bytes, data: bytes
) -> RegularFileRecord | DirectoryRecord | SymlinkRecord | MetadataRecord:
    *r, t = metadata
    r = bytes(r)
    t = chr(t)
    match t:
        case "r":
            return RegularFileRecord(
                file=PurePosixPath(data.decode("utf-8")),
                size=int(r),
                is_executable=False,
            )
        case "x":
            return RegularFileRecord(
                file=PurePosixPath(data.decode("utf-8")),
                size=int(r),
                is_executable=True,
            )
        case "d":
            return DirectoryRecord(
                directory=PurePosixPath(data.decode("utf-8")),
                children=int(r),
            )
        case "s":
            return SymlinkRecord(
                link=PurePosixPath(data.decode("utf-8")),
                target=r.decode("utf-8"),
            )
        case "p":
            return MetadataRecord(
                metadata=loads(data),
            )


# max_records = -1
def on_record(record: Record):
    print(record.metadata["name"])
    for r in record.records:
        if isinstance(r, RegularFileRecord):
            print(f"  {r.file} (size: {r.size}, executable: {r.is_executable})")
        elif isinstance(r, DirectoryRecord):
            print(f"  {r.directory} (children: {r.children})")
        elif isinstance(r, SymlinkRecord):
            print(f"  {r.link} -> {r.target}")
    # global max_records
    # if len(record.records) > max_records:
    #     print(record.metadata["name"])
    #     print("New record:", len(record.records))
    #     max_records = len(record.records)

def main():
    with open(PATH, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError("Invalid magic number")
        version = struct.unpack("<Q", f.read(8))[0]
        if version != FORMAT_VERSION:
            raise ValueError("Unsupported format version")
        with zstd.ZstdFile(f) as zf:
            records = []
            crecords: list[Record] = []
            decoder = Decoder(zf)
            for meta, path in decoder:
                # print(meta, path)
                p = decode_pair(meta, path)
                if isinstance(p, MetadataRecord):
                    if records:
                        combined_record = Record(
                            metadata=p.metadata, records=records.copy()
                        )
                        records.clear()
                        # crecords.append(combined_record)
                        on_record(combined_record)
                else:
                    records.append(p)


if __name__ == "__main__":
    main()
