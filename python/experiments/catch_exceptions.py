import sys
from types import FrameType
from typing import Any

from IPython.terminal.embed import InteractiveShellEmbed


class catch_exceptions:
    """Catch and collect exceptions."""

    def __init__(self, *exceptions: type[BaseException]):
        if not exceptions:
            exceptions = (Exception,)
        self.exceptions_to_catch = exceptions
        self.exceptions: list[BaseException] = []

    def tracer(self, frame: FrameType, event: str, arg: Any):
        if event == "exception":
            exc_type, exc_value, _ = arg
            if issubclass(exc_type, self.exceptions_to_catch):
                self.exceptions.append(exc_value)
        return self.tracer

    def start_tracing(self) -> None:
        sys.settrace(self.tracer)

    def stop_tracing(self) -> None:
        sys.settrace(None)

    def __enter__(self):
        self.start_tracing()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: Any,
    ) -> bool:
        self.stop_tracing()
        if exc_type is not None and issubclass(exc_type, self.exceptions_to_catch):
            self.exceptions.append(exc_value)
            return True  # Suppress the exception
        return False  # Do not suppress other exceptions


def lol(err: Exception) -> None:
    try:
        raise err
    except Exception:
        pass


# with catch_exceptions(ValueError, KeyError, TypeError) as catcher:
#     lol(ValueError("This is a ValueError"))
#     lol(KeyError("This is a KeyError"))
#     raise TypeError("This is a TypeError")
# print(
#     catcher.exceptions
# )  # Output: [ValueError('This is a ValueError'), KeyError('This is a KeyError')]
with catch_exceptions() as c:
    sh = InteractiveShellEmbed()
    sh()
print(len(c.exceptions))
