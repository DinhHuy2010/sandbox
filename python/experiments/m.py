from math import perm as P, comb as C
from typing import Callable, Self


class Printer:
    def __rrshift__(self, other: object) -> Self:
        print(other)
        return self


class temp:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def __rlshift__[T](self, other: Callable[..., T]) -> T:
        return other(*self.args, **self.kwargs)


o = Printer()

(P(5, 2)) >> o  # 20
(C(5, 2)) >> o  # 10
"Hello, world!" >> o

greet = "Hello, {}!".format
print(greet("Alice"))  # Hello, Alice!
(greet << temp("Alice")) >> o  # Hello, Alice!
