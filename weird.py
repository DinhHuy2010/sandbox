from types import SimpleNamespace
from typing import Any, Callable


class Extendable(SimpleNamespace):
    __repr__ = object.__repr__


def stuff(__ex__: Callable[..., Extendable] = Extendable, /, **__more: Any):
    return __ex__(**__more)


result = stuff(o=Extendable)
print(result.o())  # Output: I'm new here!
