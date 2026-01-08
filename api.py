from __future__ import annotations
from hashlib import new
from io import TextIOWrapper, RawIOBase
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from typing import Protocol
    from _typeshed import ReadableBuffer

    class Hash(Protocol):
        def update(self, data: ReadableBuffer) -> None: ...
        def digest(self) -> bytes: ...
        def hexdigest(self) -> str: ...


class HasherIO(RawIOBase):
    def __init__(self, hashfn: str | Hash | Callable[[], Hash]) -> None:
        if isinstance(hashfn, str):
            self._hasher = new(hashfn)
        elif callable(hashfn):
            self._hasher = hashfn()
        else:
            self._hasher = hashfn
        self._closed = False

    def write(self, data: ReadableBuffer) -> int:
        if self._closed:
            raise ValueError("I/O operation on closed file.")
        self._hasher.update(data)
        return len(data)  # type: ignore

    def update(self, data: ReadableBuffer) -> None:
        self.write(data)

    def digest(self) -> bytes:
        return self._hasher.digest()

    def hexdigest(self) -> str:
        return self._hasher.hexdigest()

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return False

    @property
    def name(self) -> str:
        return f"hasher-{id(self):x}"

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def truncate(self, size: int | None = None) -> int:
        raise NotImplementedError("HasherIO object is not seekable")

    def tell(self) -> int:
        raise NotImplementedError("HasherIO object is not seekable")

    def read(self, size: int | None = None) -> bytes:
        raise NotImplementedError("HasherIO object is not readable")

    def fileno(self) -> int:
        raise NotImplementedError("HasherIO object does not have a file descriptor")

    def isatty(self) -> bool:
        return False


# Example usage

h = HasherIO("sha256")
hs = TextIOWrapper(h)
hs.write("Hello, World!")
print(h.hexdigest())
