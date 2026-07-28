import sys
from typing import TYPE_CHECKING, Any, Callable, Iterable


class gototype(Exception):
    def __init__(self, **kwargs):
        super().__init__()
        self.__dict__.update(kwargs)

    def __str__(self):
        return "goto " + self.__class__.__name__


class Print(gototype):
    if TYPE_CHECKING:

        def __init__(self, *, message: str): ...


class If(gototype):
    if TYPE_CHECKING:

        def __init__(
            self, *, condition: bool, true: Callable[[], Any], false: Callable[[], Any]
        ): ...


class For(gototype):
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            iterable: Iterable[Any],
            body: Callable[[Any], Any],
            else_: Callable[[], Any] | None = None,
        ): ...


class While(gototype):
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            condition: Callable[[], bool],
            body: Callable[[], Any],
            else_: Callable[[], Any] | None = None,
        ): ...


def _excepthook(exc_type, exc_value, exc_traceback):
    def handle_For(iterable, body, else_):
        for item in iterable:
            body(item)
        if else_ is not None:
            else_()

    def handle_While(condition, body, else_):
        while condition():
            body()
        if else_ is not None:
            else_()

    state = {
        Print: lambda message: print(message),
        If: lambda condition, true, false: (true, false)[not condition](),
        For: handle_For,
        While: handle_While,
    }
    state.get(exc_type, lambda **kwargs: None)(**exc_value.__dict__)


sys.excepthook = _excepthook


def goto(p: gototype):
    raise p from None


def goto_without_stop(p: gototype):
    _excepthook(type(p), p, p.__traceback__)


def main():
    goto_without_stop(Print(message="Hello, World!"))
    # goto_without_stop(Print(message="Hello, World!"))
    goto_without_stop(
        For(
            iterable=range(3),
            body=lambda x: goto_without_stop(Print(message=f"Number: {x}")),
            else_=lambda: goto_without_stop(Print(message="Done")),
        )
    )


goto(If(condition=__name__ == "__main__", true=main, false=lambda: None))
