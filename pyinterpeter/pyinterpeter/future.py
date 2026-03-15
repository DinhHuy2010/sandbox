from __future__ import annotations
from typing import Any, Callable

from pyinterpeter.constants import OPERATORS


def resolve_future[T](future_or_object: T | Future[T]) -> T:
    if isinstance(future_or_object, Future):
        return future_or_object.resolve()
    return future_or_object


def _filler_for_future_meta():
    def create_factory(func: Callable[[Any, Any], Any]):
        def op(self: Any, other: Any) -> Any:
            return func(resolve_future(self), resolve_future(other))

        return op

    return {meth: create_factory(func) for func, meth in OPERATORS.values()}


class FutureMeta(type):
    @classmethod
    def __prepare__(metacls, name, bases, /, **kwds):
        ns = super().__prepare__(name, bases, **kwds)
        ns.update(_filler_for_future_meta())
        return ns


class Future[T](metaclass=FutureMeta):
    def __init__(
        self, fn: Callable[..., T], args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def _is_cached(self) -> bool:
        return hasattr(self, "result")

    def resolve(self) -> T:
        if self._is_cached():
            return getattr(self, "result")
        result = self.fn(*self.args, **self.kwargs)
        setattr(self, "result", result)
        return result

    def __repr__(self) -> str:
        return f"<future at 0x{id(self):08x}>"
