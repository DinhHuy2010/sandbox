# pyright: standard

from __future__ import annotations

from typing import Sequence, SupportsIndex, overload


class indexable_cycle[T]:
    def __init__(self, container: Sequence[T]) -> None:
        self._container = container
        self._length = len(container)

    # ic[0]
    @overload
    def __getitem__(self, index: SupportsIndex) -> T: ...
    # ic[5:] OR ic[5::2]
    @overload
    def __getitem__(
        self, index: slice[int, None, int | None]
    ) -> indexable_cycle[T]: ...
    @overload
    # ic[5:20] OR ic[5:20:5]
    def __getitem__(self, index: slice[int, int, int | None]) -> list[T]: ...
    def __getitem__(
        self, index: SupportsIndex | slice[int, int | None, int | None]
    ) -> T | indexable_cycle[T] | list[T]:
        if self._length == 0:
            raise IndexError("Cannot index into an empty container.")
        if isinstance(index, slice):
            start = index.start if index.start is not None else 0
            stop = index.stop
            step = index.step if index.step is not None else 1
            if stop is None:
                begin = self._container[start::step]
                return indexable_cycle(begin)
            else:
                begin = self._container[start:]
                full_cycles, remainder = divmod((stop - start) // step, self._length)
                result: list[T] = []
                result.extend(begin)
                for _ in range(full_cycles):
                    result.extend(self._container)
                result.extend(self._container[: remainder * step : step])
                return result
        else:
            wrapped_index = int(index) % self._length
            return self._container[wrapped_index]
        raise NotImplementedError("Slicing is not supported")


ic = indexable_cycle([1, 2, 3])
print(ic[999])
