from typing import Any, Callable


def invoke[T](*args: Any, **kwargs: Any) -> Callable[[Callable[..., T]], T]:
    """A generic function that simulates invoking a callable and returning a value of type T."""

    def inner(f: Callable[..., T]) -> T:
        return f(*args, **kwargs)

    return inner

# @invoke()
# @invoke()
# @invoke(1, 2)
def add(x: int, y: int):
    return lambda: lambda: x + y

invoke()(lambda: 42)
