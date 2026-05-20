from inspect import getsource, getsourcelines
import linecache
from pprint import pprint
import sys
from types import FrameType
from typing import Any

from pydantic import ConfigDict, PydanticUserError, TypeAdapter


class _Cast:
    def __init__(self, pydantic_config: ConfigDict | None = None) -> None:
        self.__pydantic_config__ = pydantic_config or ConfigDict()

    def __call__[T](self, typ: type[T] | Any, val: Any) -> T:
        """
        Like typing.cast, but with pydantic runtime validation/coercion.

        If the provided type cannot be handled by Pydantic and it raises
        PydanticUserError, the original value is returned unchanged.
        Validation errors for incompatible values are still raised.
        """

        try:
            return TypeAdapter(typ, config=self.__pydantic_config__).validate_python(
                val
            )
        except PydanticUserError:
            return val


cast = _Cast()


def update_pydantic_config(config: ConfigDict):
    """
    Change the pydantic config used by the cast function.
    """
    cast.__pydantic_config__.update(config)


def _trace(frame: FrameType, event, arg):
    def print_frame(frame: FrameType) -> None:
        lineno = frame.f_lineno
        filename = frame.f_code.co_filename
        function_name = frame.f_code.co_name
        print(f"-> {filename}:{lineno} at {function_name}")
        line = linecache.getline(filename, lineno).strip()
        if line:
            print(f"   {lineno} | {line}")

    print_frame(frame)
    return _trace


def main():
    p = cast(list[int], ["1", "2", "3"])  # [1, 2, 3]
    print(p)


if __name__ == "__main__":
    try:
        sys.settrace(_trace)
        main()
    except KeyboardInterrupt:
        pass
