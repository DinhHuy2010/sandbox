# pyright: standard

from __future__ import annotations

from io import StringIO
from pathlib import Path
from types import TracebackType

from pydantic import Field, JsonValue
from pydantic.dataclasses import dataclass


@dataclass
class Details:
    info: dict[str, JsonValue] = Field(
        ..., description="Additional details about the error"
    )
    uri: str = Field(..., description="URI related to the error")

    @classmethod
    def from_traceback(cls, tb: TracebackType) -> Details:
        info: dict[str, JsonValue] = {}
        frame = tb.tb_frame
        info["filename"] = frame.f_code.co_filename
        info["lineno"] = tb.tb_lineno
        info["locals"] = [k for k in frame.f_locals.keys()]
        info["globals"] = [k for k in frame.f_globals.keys()]

        uri = Path(frame.f_code.co_filename).as_uri()
        if tb.tb_lineno:
            uri += f"#L{tb.tb_lineno}"

        return cls(info=info, uri=uri)


@dataclass
class Error:
    code: str = Field(..., description="Error code", pattern=r"^[a-zA-Z0-9_-]+$")
    message: str = Field(..., description="Error message")
    caused_by: Error | None = Field(
        None, description="Nested error that caused this error"
    )
    details: Details | None = Field(
        None, description="Additional details about the error"
    )

    @classmethod
    def from_exception(cls, exc: BaseException) -> Error:
        def generate_name(exc: BaseException) -> str:
            if isinstance(exc, KeyError):
                return "key-error"
            elif isinstance(exc, ValueError):
                return "value-error"
            elif isinstance(exc, TypeError):
                return "type-error"
            elif isinstance(exc, ZeroDivisionError):
                return "zero-division-error"
            else:
                return f"py-exception-{exc.__class__.__name__}"

        return cls(
            code=generate_name(exc),
            message=str(exc),
            caused_by=cls.from_exception(_)
            if (_ := exc.__cause__ or exc.__context__)
            else None,
            details=Details.from_traceback(exc.__traceback__)
            if exc.__traceback__
            else None,
        )

    def format(self) -> str:
        output = StringIO()
        stacks: list[tuple[Error, int]] = [(self, 0)]
        while stacks:
            current, level = stacks.pop()
            indent = " " * min(level, 3) * 4
            output.write(f"{indent}{current.code}: {current.message}\n")
            output.write(f"{indent}Details:\n")
            if current.details:
                for key, value in current.details.info.items():
                    output.write(f"{indent}  {key}: {value}\n")
                output.write(f"{indent}  URI: {current.details.uri}\n")

            if current.caused_by:
                if level < 3:
                    output.write(f"{indent}Caused by:\n")
                stacks.append((current.caused_by, level + 1))
        return output.getvalue()


try:
    1 / 0
except ZeroDivisionError as e:
    error = Error.from_exception(e)
    print(error.format())
