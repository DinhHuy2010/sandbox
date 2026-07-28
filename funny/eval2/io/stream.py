from __future__ import annotations

import builtins
from dataclasses import dataclass
from typing import IO, Any

from eval2.core import Evaluatable, EvaluatableOrValue, evaluate_value
from eval2.builtins import Expression, Value, evaluatable_or_value


@dataclass
class IOExpression[DataType]:
    io_value: Evaluatable[IO[DataType]]

    def evaluate(self, ctx) -> IO[DataType]:
        io_value = evaluate_value(self.io_value, ctx)
        return io_value

    def read(self, size: int = -1) -> Expression[DataType]:
        def evaluate(ctx):
            io_value = self.evaluate(ctx)
            return io_value.read(size)

        return Expression(evaluate)

    def write(self, data: DataType) -> Expression[int]:
        def evaluate(ctx):
            io_value = self.evaluate(ctx)
            return io_value.write(data)

        return Expression(evaluate)

    def seek(self, offset: int, whence: int = 0) -> IOExpression[DataType]:
        def evaluate(ctx):
            io_value = self.evaluate(ctx)
            io_value.seek(offset, whence)
            return io_value

        return IOExpression(Expression(evaluate))

    def print(
        self,
        *args: EvaluatableOrValue[object],
        sep: EvaluatableOrValue[str] = Value(" "),
        end: EvaluatableOrValue[str] = Value("\n"),
    ) -> Expression[None]:
        def evaluate(ctx):
            io_value = self.evaluate(ctx)
            print(
                *(evaluate_value(evaluatable_or_value(arg), ctx) for arg in args),
                sep=evaluate_value(evaluatable_or_value(sep), ctx),
                end=evaluate_value(evaluatable_or_value(end), ctx),
                file=io_value,
            )

        return Expression(evaluate)

    def flush(self) -> IOExpression[DataType]:
        def evaluate(ctx):
            io_value = self.evaluate(ctx)
            io_value.flush()
            return io_value

        return IOExpression(Expression(evaluate))


def input(prompt: EvaluatableOrValue[str] = Value("")) -> Expression[str]:
    prompt = evaluatable_or_value(prompt)

    def evaluate(ctx):
        prompt_value = evaluate_value(prompt, ctx)
        return builtins.input(prompt_value)

    return Expression(evaluate)


def open_text(
    path: EvaluatableOrValue[Any], mode: EvaluatableOrValue[str] = Value("r")
) -> IOExpression[str]:
    def evaluate(ctx):
        path_value = evaluate_value(evaluatable_or_value(path), ctx)
        mode_value = evaluate_value(evaluatable_or_value(mode), ctx)
        return open(path_value, mode_value, encoding="utf-8")

    return IOExpression(Expression(evaluate))


def open_binary(
    path: EvaluatableOrValue[Any], mode: EvaluatableOrValue[str] = Value("r")
) -> IOExpression[bytes]:
    def evaluate(ctx):
        path_value = evaluate_value(evaluatable_or_value(path), ctx)
        mode_value = evaluate_value(evaluatable_or_value(mode), ctx)
        return open(path_value, mode_value + "b")

    return IOExpression(Expression(evaluate))
