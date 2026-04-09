from abc import ABC, abstractmethod
import io
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, NoReturn
from warnings import warn

import httpx


def supports_range(url: Any, client: httpx.Client) -> int:
    """
    Check if the URL supports range requests by sending a HEAD request.
    If supported, return the content length. Otherwise, return -1.

    Parameters
    ----------
    url : Any
        The URL to check for range support.
    client : httpx.Client
        An instance of httpx.Client to use for making the request.

    Returns
    -------
    int
        The content length if range requests are supported, otherwise -1.
    """
    try:
        response = client.head(url, timeout=5.0, follow_redirects=True)
    except httpx.RequestError:
        return -1
    else:
        if response.headers.get("Accept-Ranges", "").lower() != "bytes":
            return -1
        length = response.headers.get("Content-Length")
        if length is None:
            return -1
        try:
            return int(length)
        except ValueError:
            return -1


def supports_range_flexible(url: Any, client: httpx.Client) -> int:
    """
    Check if the URL supports range requests by sending a GET request with a byte range of "0-0".
    If supported, return the total content length from the Content-Range header. Otherwise, return -1.

    Parameters and returns are the same as `supports_range()`.
    """
    try:
        response = client.get(
            url,
            headers={"Range": "bytes=0-0"},
            timeout=5.0,
            follow_redirects=True,
        )
    except httpx.RequestError:
        return -1

    if response.status_code != 206:
        return -1

    content_range = response.headers.get("Content-Range")
    if not content_range:
        return -1

    # Expected form: "bytes 0-0/123456"
    try:
        _, range_spec = content_range.split(" ", 1)
        _, total_size = range_spec.split("/")
        return int(total_size)
    except (ValueError, TypeError):
        return -1


class BaseStorage(ABC):
    @abstractmethod
    def get(self, uri: str, start: int, end: int) -> bytes | None:
        """Get a block of data from the cache for the specified byte range. Returns None if not found."""
        return None

    @abstractmethod
    def store(self, uri: str, start: int, end: int, data: bytes) -> None:
        """Store a block of data in the cache for the specified byte range."""
        return None

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached data."""
        return None

    @abstractmethod
    def close(self) -> None:
        """Close the storage and release any resources."""
        return None

    def __enter__(self) -> "BaseStorage":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class NaiveStorage(BaseStorage):
    """A simple in-memory storage implementation that does not persist data across instances."""

    def __init__(self):
        self._cache: dict[tuple[str, int, int], bytes] = {}

    def get(self, uri: str, start: int, end: int) -> bytes | None:
        return self._cache.get((uri, start, end))

    def store(self, uri: str, start: int, end: int, data: bytes) -> None:
        self._cache[(uri, start, end)] = data

    def clear(self) -> None:
        self._cache.clear()

    def close(self) -> None:
        self.clear()


class LRUStorage(BaseStorage):
    """An in-memory storage implementation that evicts least recently used blocks when the cache exceeds a specified maximum number of blocks."""

    def __init__(self, max_blocks: int = 32):
        self._cache: OrderedDict[tuple[str, int, int], bytes] = OrderedDict()
        self.max_blocks = max_blocks

    def get(self, uri: str, start: int, end: int) -> bytes | None:
        key = (uri, start, end)
        data = self._cache.get(key)
        if data is not None:
            self._cache.move_to_end(key)
        return data

    def store(self, uri: str, start: int, end: int, data: bytes) -> None:
        key = (uri, start, end)
        self._cache[key] = data
        self._cache.move_to_end(key)
        while len(self._cache) > self.max_blocks:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()

    def close(self) -> None:
        self.clear()


@dataclass
class HTTPFile(io.IOBase):
    """
    File-like object that reads from an HTTP resource using range requests for efficient access.

    Note: Server MUST support range requests for this to work. The class will attempt to determine the content length and range support on initialization.
    If the server does not support range requests, it will raise a ValueError when trying to read.
    """

    url: str | httpx.URL
    """URL of the HTTP resource to read from."""
    client: httpx.Client = field(default_factory=httpx.Client, repr=False)
    """HTTP client used for making requests."""
    flexible_range: bool = False
    """Whether to use flexible range requests check."""
    block_size: int = 64 * 1024
    """Size of each block to fetch in bytes."""
    verbose: bool = False
    """Whether to print debug information about operations."""
    storage: BaseStorage = field(default=None)
    """Storage backend for caching fetched blocks."""

    def __post_init__(self) -> None:
        self._position: int = 0
        self._length: int | None = None
        if self.storage is None:
            self.storage = LRUStorage(max_blocks=self.max_blocks)

    def _log(self, message: str) -> None:
        if self.verbose:
            print("[rangeresp]", message, file=sys.stderr)

    def _fetch_length(self) -> int:
        if self.flexible_range:
            length = supports_range_flexible(self.url, self.client)
        else:
            length = supports_range(self.url, self.client)

        if length == -1:
            raise ValueError(f"URL does not support range requests: {self.url}")
        return length

    def _fetch_range(self, start: int, end: int) -> httpx.Response:
        response = self.client.get(
            self.url,
            headers={"Range": f"bytes={start}-{end}"},
            timeout=5.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        if response.status_code != 206:
            raise IOError(
                f"Expected 206 Partial Content, got {response.status_code} "
                f"for range {start}-{end}"
            )
        return response

    @property
    def length(self) -> int:
        """Get the total length of the HTTP resource. This is determined by checking if the server supports range requests."""
        if self._length is None:
            self._length = self._fetch_length()
        return self._length

    def readable(self) -> bool:
        """Indicates that the file-like object supports reading."""
        try:
            _ = self.length  # Ensure length can be determined
        except ValueError:
            # Cannot determine length, likely because range requests are not supported
            return False
        return True

    def seekable(self) -> bool:
        """Indicates that the file-like object supports seeking."""
        return True

    def tell(self) -> int:
        """Get the current position in the file-like object."""
        return self._position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        """Seek to a new position in the file-like object based on the offset and whence. Returns the new position."""
        self._log(f"Seeking to offset {offset} with whence {whence}")

        if whence == io.SEEK_SET:
            new_position = offset
        elif whence == io.SEEK_CUR:
            new_position = self._position + offset
        elif whence == io.SEEK_END:
            new_position = self.length + offset
        else:
            raise ValueError(f"Invalid whence value: {whence}")

        if new_position < 0:
            raise ValueError("Negative seek position is not allowed")

        self._position = new_position
        return self._position

    def _parse_content_range(
        self,
        header_value: str | None,
        expected_start: int,
        expected_end: int,
        expected_total: int,
    ) -> bool:
        """Parse the Content-Range header and validate it against expected values. Returns True if valid, False otherwise."""
        if not header_value:
            return False
        try:
            unit, rest = header_value.split(" ", 1)
            if unit.lower() != "bytes":
                return False

            range_part, total_part = rest.split("/", 1)
            start_str, end_str = range_part.split("-", 1)

            start = int(start_str)
            end = int(end_str)
            total = int(total_part)

            return (
                start == expected_start
                and end == expected_end
                and total == expected_total
            )
        except (ValueError, TypeError):
            return False

    def _fetch_block(self, block_index: int) -> bytes:
        """Fetch a block of data from the HTTP resource, using caching to avoid redundant requests."""

        cached = self.storage.get(
            str(self.url),
            block_index * self.block_size,
            (block_index + 1) * self.block_size - 1,
        )
        if cached is not None:
            self._log(f"Cache hit for block {block_index}")
            return cached

        block_start = block_index * self.block_size
        block_end = min(block_start + self.block_size, self.length) - 1

        self._log(f"Fetching block {block_index}: bytes={block_start}-{block_end}")

        response = self._fetch_range(block_start, block_end)

        if not self._parse_content_range(
            response.headers.get("Content-Range"),
            expected_start=block_start,
            expected_end=block_end,
            expected_total=self.length,
        ):
            raise IOError(
                f"Invalid Content-Range for block {block_index}: "
                f"{response.headers.get('Content-Range')!r}"
            )

        data = response.content
        expected_len = block_end - block_start + 1

        if len(data) < expected_len:
            raise IOError(
                f"Incomplete block read for block {block_index}: "
                f"expected {expected_len} bytes, got {len(data)}"
            )
        elif len(data) > expected_len:
            warn(
                f"Received more data than expected for block {block_index}: "
                f"expected {expected_len} bytes, got {len(data)}. ",
                stacklevel=2,
            )

        self.storage.store(
            str(self.url),
            block_index * self.block_size,
            (block_index + 1) * self.block_size - 1,
            data,
        )
        return data

    def read(self, size: int = -1) -> bytes:
        """Read up to `size` bytes from the file-like object. If `size` is negative, read until the end of the file."""
        self._log(f"Reading {size} bytes from position {self._position}")

        if self._position >= self.length:
            return b""

        if size < 0:
            size = self.length - self._position

        if size == 0:
            return b""

        end_position = min(self._position + size, self.length)
        chunks: list[bytes] = []

        while self._position < end_position:
            block_index = self._position // self.block_size
            block = self._fetch_block(block_index)

            block_start = block_index * self.block_size
            offset_in_block = self._position - block_start
            available_in_block = len(block) - offset_in_block
            remaining = end_position - self._position
            take = min(available_in_block, remaining)

            chunks.append(block[offset_in_block : offset_in_block + take])
            self._position += take

        return b"".join(chunks)

    def close(self) -> None:
        """Close the file-like object and release any resources. This will clear the cache and close the HTTP client."""
        self.storage.close()
        self.client.close()
        super().close()

    @property
    def name(self) -> str:
        """Return the name of the file-like object, which is the URL."""
        return str(self.url)


def open_http(
    url: httpx.URL | str,
    client: httpx.Client | None = None,
    flexible_range: bool = True,
    block_size: int = 64 * 1024,
    max_blocks: int = 32,
    verbose: bool = False,
) -> HTTPFile:
    """
    Open an HTTP resource as a file-like object that supports efficient reading using range requests.

    Parameters
    ----------
    url : httpx.URL | str
        The URL of the HTTP resource to open.
    client : httpx.Client | None, optional
        An optional httpx.Client instance to use for making requests. If None, a new client
        will be created for this file.
    flexible_range : bool, default True
        Whether to use the flexible range check (GET with Range: bytes=0-0)
        to determine content length and range support. If False, a HEAD request will be used instead.
    block_size : int, default 65536
        The size of each block to fetch in bytes. This determines how much data is fetched in
        each range request. A larger block size may reduce the number of requests but increase memory usage.
    max_blocks : int, default 32
        The maximum number of blocks to keep in the cache. Once the cache exceeds this number,
        the least recently used blocks will be evicted. This helps manage memory usage while still
        providing efficient access to recently read data.
    verbose : bool, default False
        Whether to print debug information about operations to stderr. This can be useful for troubleshooting
        or understanding the behavior of the file-like object, especially when dealing with caching and range requests.

    Returns
    -------
    HTTPFile
        A file-like object that can be used to read from the specified HTTP resource using range requests.

    Raises
    ------
    ValueError
        If the URL does not support range requests, a ValueError will be raised when trying to
        read from the file-like object.
    """
    if client is None:
        client = httpx.Client()
    return HTTPFile(
        url=url,
        client=client,
        flexible_range=flexible_range,
        block_size=block_size,
        verbose=verbose,
        storage=LRUStorage(max_blocks=max_blocks),
    )


def property_not_supported(name: str) -> property:
    def _not_supported(self: "HTTPStatResult") -> NoReturn:
        raise NotImplementedError(
            f"The property '{name}' is not supported for HTTPStatResult"
        )

    return property(_not_supported)


@dataclass(frozen=True)
class HTTPStatResult:
    st_size: int
    st_mode: int = field(init=False, default=0o100644)
    st_ino: int = field(init=False, default=0)
    st_dev: int = field(init=False, default=0)
    st_nlink: int = field(init=False, default=1)
    st_uid: int = field(init=False, default=0)
    st_gid: int = field(init=False, default=0)

    st_atime = property_not_supported("st_atime")
    st_mtime = property_not_supported("st_mtime")
    st_ctime = property_not_supported("st_ctime")


def stat(
    http_file: str | httpx.URL, client: httpx.Client | None = None
) -> HTTPStatResult:
    """
    Get the file-like stat information for an HTTP resource. This function checks if the URL supports range requests and retrieves the content length to populate the st_size field of the HTTPStatResult. Other fields are set to default values since they are not applicable to HTTP resources.

    Parameters
    ----------
    http_file : str | httpx.URL
        The URL of the HTTP resource to stat.
    client : httpx.Client | None, optional
        An optional httpx.Client instance to use for making requests. If None, a new client
        will be created for this operation.

    Returns
    -------
    HTTPStatResult
        An object containing the stat information for the HTTP resource, including the size (st_size)

    """
    if client is None:
        client = httpx.Client()
    length = supports_range_flexible(http_file, client)
    return HTTPStatResult(st_size=length)
