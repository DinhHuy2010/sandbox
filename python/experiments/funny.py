from __future__ import annotations

from typing import Any, Iterable, MutableSequence, overload

def grab_item(ls: InteractiveList[Any], index_or_slice: int | slice) -> Any:
    if isinstance(index_or_slice, slice):
        print(f"Getting slice {index_or_slice} from InteractiveList")
    else:
        print(f"Getting index {index_or_slice} from InteractiveList")
    value = ls.data[index_or_slice]
    print(f"Value obtained: {value}")
    while True:
        p = input("(A)pprove/(D)eny? ").strip().lower()
        if p in {"a", "approve", ""}:
            break
        elif p in {"d", "deny"}:
            raise PermissionError("Access to the requested item was denied by the user.")
    if isinstance(index_or_slice, slice):
        return InteractiveList(value)
    return value

class InteractiveList[T](MutableSequence[T]):
    def __init__(self, initial: list[T] | None = None) -> None:
        self.data: list[T] = initial if initial is not None else []

    @overload
    def __getitem__(self, index_or_slice: int) -> T: ...
    @overload
    def __getitem__(self, index_or_slice: slice) -> "InteractiveList[T]": ...
    def __getitem__(self, index_or_slice: int | slice) -> "T | InteractiveList[T]":
        return grab_item(self, index_or_slice)

    @overload
    def __setitem__(self, index_or_slice: int, value: T) -> None: ...
    @overload
    def __setitem__(self, index_or_slice: slice, value: Iterable[T]) -> None: ...
    def __setitem__(self, index_or_slice: int | slice, value: T | Iterable[T]) -> None:
        self.data[index_or_slice] = value  # type: ignore

    def __delitem__(self, index_or_slice: int | slice) -> None:
        del self.data[index_or_slice]

    def __len__(self) -> int:
        return len(self.data)

    def insert(self, index: int, value: T) -> None:
        self.data.insert(index, value)

    def __str__(self) -> str:
        return f"InteractiveList({self.data})"

    def append(self, value: T) -> None:
        self.data.append(value)

    def pop(self, index: int = -1) -> T:
        return self.data.pop(index)

    def clear(self) -> None:
        self.data.clear()


ls = InteractiveList([1, 2, 3])
print(ls[0])  # InteractiveList([1, 2, 3])
