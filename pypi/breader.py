from typing import IO, Any, Iterable


def rechunk(iterable: Iterable[bytes], chunk_size: int) -> Iterable[bytes]:
    buffer = bytearray()

    for item in iterable:
        buffer.extend(item)
        while len(buffer) >= chunk_size:
            yield bytes(buffer[:chunk_size])
            del buffer[:chunk_size]

    if buffer:
        yield bytes(buffer)


class BReader(IO[bytes]):
    def __init__(self, iterable: Iterable[bytes]) -> None:
        self._iterator = iter(iterable)
        self._buffer = bytearray()
        self._eof = False
        self._closed = False
        self._pos = 0

    def _fill(self, n: int | None = None) -> None:
        if self._eof:
            return

        try:
            while n is None or len(self._buffer) < n:
                self._buffer.extend(next(self._iterator))
        except StopIteration:
            self._eof = True

    def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        if size == 0:
            return b""

        if size < 0:
            self._fill(None)
            data = bytes(self._buffer)
            self._buffer.clear()
        else:
            self._fill(size)
            data = bytes(self._buffer[:size])
            del self._buffer[:size]

        self._pos += len(data)
        return data

    def readline(self, limit: int = -1) -> bytes:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        while True:
            idx = self._buffer.find(b"\n")
            if idx != -1:
                idx += 1
                break

            if self._eof:
                idx = len(self._buffer)
                break

            self._fill(None)

        if limit >= 0:
            idx = min(idx, limit)

        line = bytes(self._buffer[:idx])
        del self._buffer[:idx]
        self._pos += len(line)
        return line

    def readinto(self, b: bytearray) -> int:
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)

    def tell(self) -> int:
        return self._pos

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> "BReader":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
