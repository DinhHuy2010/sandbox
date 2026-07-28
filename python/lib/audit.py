import reprlib
import sys
from contextlib import contextmanager, redirect_stdout
from typing import Any, Callable, Protocol

type Unused = Any
type C = Callable[..., Any]


class AuditHook(Protocol):
    __events__: set[str]
    __call__: Callable[..., Unused]
    __wrapped__: Callable[..., Unused]


hooks: dict[str, list[AuditHook]] = {}


def handle_for_audit(*events: str) -> Callable[[C], C]:
    def decorator(func: C) -> C:
        func.__events__ = set(events)
        func.__wrapped__ = func
        for event in events:
            hooks.setdefault(event, []).append(func)
        return func

    return decorator


@contextmanager
def _context():
    import builtins

    orig_print = builtins.print
    orig_repr = builtins.repr

    def new_print(*args: Any, **kwargs: Any):
        orig_print(">>>", *args, **kwargs)

    try:
        builtins.print = new_print
        builtins.repr = reprlib.repr
        with redirect_stdout(sys.stderr):
            yield
    finally:
        builtins.print = orig_print
        builtins.repr = orig_repr


def audithook(event: str, args: Any) -> None:
    with _context():
        for hook in hooks.get(event, []):
            hook(*args)


def inject() -> None:
    sys.addaudithook(audithook)


if __name__ == "__main__":
    inject()
