# pyright: standard

import io
from collections import OrderedDict, UserDict
from dataclasses import dataclass, field
from typing import Literal, Protocol

import httpx


def _get_length(url: str, client: httpx.Client) -> int:
    response = client.head(url)
    response.raise_for_status()
    if response.headers.get("Accept-Ranges") != "bytes":
        raise OSError("Server does not support byte ranges")
    content_length = response.headers.get("Content-Length")
    if content_length is None:
        raise OSError("Missing Content-Length")
    return int(content_length)


def _get_length_by_GET(url: str, client: httpx.Client) -> int:
    response = client.get(url, headers={"Range": "bytes=0-0"})
    response.raise_for_status()
    if response.status_code != 206:
        raise IOError(f"Expected partial content (206), got {response.status_code}")
    if response.headers.get("Accept-Ranges") != "bytes":
        raise OSError("Server does not support byte ranges")
    content_range = response.headers.get("Content-Range")
    if content_range is None:
        raise OSError("Missing Content-Range")
    _, _, total_length = content_range.partition("/")
    return int(total_length)


class CachingDictMapping(Protocol):
    def __getitem__(self, key: int) -> bytes: ...
    def __setitem__(self, key: int, value: bytes) -> None: ...
    def __contains__(self, key: object) -> bool: ...


class PassThroughMapping(CachingDictMapping):
    def __getitem__(self, key: int) -> bytes:
        raise KeyError(key)

    def __setitem__(self, key: int, value: bytes) -> None:
        pass

    def __contains__(self, key: object) -> bool:
        return False

    def clear(self) -> None:
        pass


class GrowOnlyMapping(UserDict[int, bytes], CachingDictMapping):
    pass


class LRUMapping(OrderedDict[int, bytes], CachingDictMapping):
    def __init__(self, max_size: int):
        super().__init__()
        self.max_size = max_size

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.max_size:
            self.popitem(last=False)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value


@dataclass(repr=False)
class HTTPFile(io.RawIOBase):
    url: str
    client: httpx.Client = field(default_factory=httpx.Client)
    chunk_size: int = 65536
    check_length_by_get: bool = False
    cache: CachingDictMapping = field(default_factory=PassThroughMapping)

    def __repr__(self) -> str:
        return f"HTTPFile(url={self.url!r}, size={self._size})"

    def __post_init__(self):
        super().__init__()
        if self.check_length_by_get:
            self._size = _get_length_by_GET(self.url, self.client)
        else:
            self._size = _get_length(self.url, self.client)
        self.position = 0

    def _fetch_range_from_block(self, start: int, end: int) -> bytes:
        block_start = (start // self.chunk_size) * self.chunk_size
        block_end = min(block_start + self.chunk_size, self._size)
        if block_start not in self.cache:
            content = self._fetch_range(block_start, block_end)
            block_data = self.cache[block_start] = content
        else:
            block_data = self.cache[block_start]
        offset_start = start - block_start
        offset_end = min(end - block_start, len(block_data))
        return block_data[offset_start:offset_end]

    def _fetch_range(self, start: int, end: int) -> bytes:
        # print(f"Fetching bytes {start}-{end - 1}")
        response = self.client.get(
            self.url, headers={"Range": f"bytes={start}-{end - 1}"}
        )
        response.raise_for_status()
        if response.status_code != 206:
            raise IOError(f"Expected partial content (206), got {response.status_code}")
        return response.content

    def read(self, size: int = -1) -> bytes:
        self._if_closed()
        if self.position >= self._size:
            return b""

        if size < 0:
            size = self._size - self.position

        end_position = min(self.position + size, self._size)
        parts = []
        pos = self.position

        while pos < end_position:
            part = self._fetch_range_from_block(pos, end_position)
            if not part:
                break
            parts.append(part)
            pos += len(part)

        data = b"".join(parts)
        self.position = pos
        return data

    def readinto(self, buffer) -> int:
        # use memoryview
        mv = memoryview(buffer)
        data = self.read(len(mv))
        mv[: len(data)] = data
        return len(data)

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        self._if_closed()
        if whence == io.SEEK_SET:
            new_position = offset
        elif whence == io.SEEK_CUR:
            new_position = self.position + offset
        elif whence == io.SEEK_END:
            new_position = self._size + offset
        else:
            raise ValueError("Invalid value for 'whence'")

        if new_position < 0:
            raise ValueError("negative seek position")

        self.position = new_position
        return self.position

    def tell(self) -> int:
        self._if_closed()
        return self.position

    def writable(self) -> bool:
        return False

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def close(self):
        if not self.closed:
            self.client.close()
        super().close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _if_closed(self) -> None:
        if self.closed:
            raise ValueError("I/O operation on closed file.")

    @property
    def name(self) -> str:
        return self.url

    def buffered(
        self, buffer_size: int | Literal["default"] | None = None
    ) -> io.BufferedReader:
        if buffer_size == "default":
            buffer_size = self.chunk_size

        return io.BufferedReader(self, buffer_size=self.chunk_size)
