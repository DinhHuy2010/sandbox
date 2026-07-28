# pyright: strict

from typing import TYPE_CHECKING, Callable, Concatenate, Protocol


class GenericBoundMethod[S, **P, R](Protocol):
    @property
    def __self__(self) -> S: ...
    @property
    def __func__(self) -> Callable[Concatenate[S, P], R]: ...

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...


type BoundMethod[**P, R] = GenericBoundMethod[object, P, R]


if TYPE_CHECKING:

    def cast_bound_method[**P, R, T](
        m: BoundMethod[P, R], real_owner: type[T]
    ) -> GenericBoundMethod[T, P, R]: ...
else:

    def cast_bound_method(m, real_owner):
        return m


class Example:
    def method(self, x: int) -> str:
        return f"Value: {x}"


def accept_bound_method(m: GenericBoundMethod[Example, [int], str]) -> None:
    print(m)


e = Example()
bound_method = e.method
# it passed
accept_bound_method(cast_bound_method(bound_method, Example))
