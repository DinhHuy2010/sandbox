# pyright: standard

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import sleep
from typing import Any, Callable


class Future[T](ABC):
    @abstractmethod
    def resolve(self) -> T: ...
    def is_resolved(self) -> bool | None:
        return None


class Some(Future[int]):
    def resolve(self):
        sleep(0.5)
        return 1


@dataclass(init=False)
class FutureCall[**P, T](Future[T]):
    function: Callable[P, T]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    def __init__(
        self, func: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        self.function = func
        self.args = args
        self.kwargs = kwargs

    def resolve(self) -> T:
        if hasattr(self, "result"):
            return self.result
        else:
            result = self.result = self.function(*self.args, **self.kwargs)
            return result

    def is_resolved(self):
        return hasattr(self, "result")

    def then[F](self, func: Callable[[T], F]) -> FutureCall[[], F]:
        return FutureCall(lambda: func(self.resolve()))


def add(a: int, b: int):
    return a + b


p = FutureCall(add, 1, 2)
p.then(print).resolve()
