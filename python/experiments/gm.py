# pyright: standard

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from inspect import BoundArguments, signature
from typing import Any, Callable, Concatenate, Sequence

type Function[**P, R] = Callable[P, R]
# type Middleware[**P, R] = Callable[Concatenate[Function[P, Any], P], R]
type Middleware[**P, R] = Callable[Concatenate[Function[P, Any], ...], R]


def wrap_middleware[**P, M, F](
    func: Function[P, F],
    middleware: Middleware[P, M],
) -> Function[P, F | M]:
    """
    Wraps a function with a middleware.

    Parameters
    ----------
    func : Function[P, F]
        The function to wrap.

    middleware : Middleware[P, M]
        The middleware to wrap the function with.

    Returns
    -------
    Function[P, F | M]
        The wrapped function.
    """

    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> F | M:
        return middleware(func, *args, **kwargs)

    return wrapped


def wrap_middlewares[**P, M, F](
    func: Function[P, F],
    middlewares: Sequence[Middleware[P, M]],
) -> Function[P, M | F]:
    wrapped: Function[P, Any] = func

    for middleware in reversed(middlewares):
        wrapped = wrap_middleware(wrapped, middleware)

    return wrapped


def middleware[**P, T, M](
    *middlewares: Middleware[P, M],
) -> Callable[[Function[P, T]], Function[P, T | M]]:
    def decorator(func: Function[P, T]) -> Function[P, T | M]:
        wf = wrap_middlewares(func, middlewares)
        return wf

    return decorator


@dataclass
class MiddlewareContext[R]:
    bparams: BoundArguments
    func: Callable[..., R]

    @property
    def params(self) -> dict[str, Any]:
        return self.bparams.arguments

    def next(self) -> R:
        return self.func(*self.bparams.args, **self.bparams.kwargs)

    @classmethod
    def from_middleware_args(
        cls, next: Callable[..., R], *fargs: Any, **fkwargs: Any
    ) -> MiddlewareContext[R]:
        sig = signature(next)
        bparams = sig.bind(*fargs, **fkwargs)
        return cls(bparams=bparams, func=next)

    @classmethod
    def middleware_from_context(
        cls,
        mw_ctx_func: Callable[[MiddlewareContext[R]], R],
    ) -> Middleware[..., R]:
        def middleware(next: Callable[..., R], /, *fargs: Any, **fkwargs: Any) -> R:
            ctx = MiddlewareContext.from_middleware_args(next, *fargs, **fkwargs)
            return mw_ctx_func(ctx)

        return middleware


def example_middleware(next: Callable[[int], int], /, *fargs, **fkwargs):
    ctx = MiddlewareContext.from_middleware_args(next, *fargs, **fkwargs)
    print(ctx)
    print("Before")
    result = next(*fargs, **fkwargs)
    print("After")
    return result


def example_2_middleware(next: Callable[[int], int], /, x: int):
    # print(signature(next).bind(x))
    print("Before 2")
    result = next(x)
    print("After 2")
    return result + 1


@MiddlewareContext.middleware_from_context
def example_3_middleware(ctx: MiddlewareContext[int]) -> int:
    print("Before 3")
    result = ctx.next()
    print("After 3")
    return result + 2


@middleware(example_middleware, example_2_middleware, example_3_middleware)
def example_function(x: int) -> int:
    print(f"Function called with argument: {x}")
    return x * 2


def error_handling_middleware[**P, OE](
    error_handler: Callable[[Exception], OE],
) -> Middleware[P, OE]:
    def middleware[N](next: Callable[..., N], /, *fargs: Any, **fkwargs: Any) -> N | OE:
        try:
            return next(*fargs, **fkwargs)
        except Exception as e:
            return error_handler(e)

    return middleware


def when_zero_div(err: Exception) -> int:
    return -1


@middleware(error_handling_middleware(when_zero_div))
def divide(a: int, b: int) -> int:
    return a // b


def main():
    # middlewares = [example_middleware, example_2_middleware]
    # wrapped_function = wrap_middlewares(example_function, middlewares)
    result = example_function(5)
    print(f"Result: {result}")
    print(divide(10, 2))
    print(divide(10, 0))


if __name__ == "__main__":
    main()
