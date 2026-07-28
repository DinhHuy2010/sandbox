from __future__ import annotations

import os
from dataclasses import dataclass
from os import PathLike, fsdecode
from pathlib import Path

from upath.types import ReadablePath, WritablePath

from eval2.core import Context, Evaluatable, EvaluatableOrValue, evaluate_value
from eval2.builtins import (
    Expression,
    Value,
    _BinaryExpressionMixin,
    evaluatable_or_value,
)
from eval2.io.stream import IOExpression

type PathType = str | bytes | PathLike[str] | PathLike[bytes]


@dataclass(frozen=True)
class PathExpression(_BinaryExpressionMixin):
    path: Evaluatable[PathType]

    def evaluate(self, ctx: Context) -> Path:
        path_value = evaluate_value(self.path, ctx)
        return Path(fsdecode(path_value))

    def read_text(self) -> Expression[str]:
        def evaluate(ctx: Context) -> str:
            path = self.evaluate(ctx)
            return path.read_text()

        return Expression(evaluate)

    def write_text(self, content: EvaluatableOrValue[str]) -> PathExpression:
        def evaluate(ctx: Context) -> Path:
            path = self.evaluate(ctx)
            path.write_text(evaluate_value(evaluatable_or_value(content), ctx))
            return path

        return PathExpression(Expression(evaluate))

    def read_bytes(self) -> Expression[bytes]:
        def evaluate(ctx: Context) -> bytes:
            path = self.evaluate(ctx)
            if not isinstance(path, ReadablePath):
                raise ValueError(f"Path {path} is not readable")
            return path.read_bytes()

        return Expression(evaluate)

    def write_bytes(self, content: EvaluatableOrValue[bytes]) -> PathExpression:
        def evaluate(ctx: Context) -> Path:
            path = self.evaluate(ctx)
            if not isinstance(path, WritablePath):
                raise ValueError(f"Path {path} is not writable")
            path.write_bytes(evaluate_value(evaluatable_or_value(content), ctx))
            return path

        return PathExpression(Expression(evaluate))

    def stat(self) -> Expression[os.stat_result]:
        def evaluate(ctx: Context) -> os.stat_result:
            path = self.evaluate(ctx)
            return path.stat()

        return Expression(evaluate)

    def exists(self) -> Expression[bool]:
        def evaluate(ctx: Context) -> bool:
            path = self.evaluate(ctx)
            return path.exists()

        return Expression(evaluate)

    def is_file(self) -> Expression[bool]:
        def evaluate(ctx: Context) -> bool:
            path = self.evaluate(ctx)

            return path.is_file()

        return Expression(evaluate)

    def is_dir(self) -> Expression[bool]:
        def evaluate(ctx: Context) -> bool:
            path = self.evaluate(ctx)
            return path.is_dir()

        return Expression(evaluate)

    def open_text(
        self, mode: EvaluatableOrValue[str] = Value("r")
    ) -> IOExpression[str]:
        def evaluate(ctx: Context):
            path = self.evaluate(ctx)
            mode_value = evaluate_value(evaluatable_or_value(mode), ctx)
            return open(path, mode_value)

        return IOExpression(Expression(evaluate))

    @classmethod
    def cwd(cls) -> PathExpression:
        return cls(Value(Path.cwd()))

    @classmethod
    def home(cls) -> PathExpression:
        return cls(Value(Path.home()))
