from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from eval2.builtins import Expression, Value, wrap_as_expression
from eval2.core import (
    Context,
    Evaluatable,
    EvaluatableFunction,
    evaluate_value,
    evaluate_with_context,
)


def map_iterable[F](
    evalable_iterable: Evaluatable[Iterable[Any]],
    func: EvaluatableFunction[F],
    *,
    apply_ctx: bool = False,
) -> Expression[Iterable[F]]:
    def evaluate(ctx: Context) -> Iterable[F]:
        iterable = evaluate_value(evalable_iterable, ctx)
        return (
            evaluate_with_context(
                func,
                ctx=ctx.set_value(Value(item))
                if apply_ctx
                else Context(value=Value(item)),
            )[1]
            for item in iterable
        )

    return Expression(evaluate)


_list_expr = wrap_as_expression(list)


def map_list[F](
    array: Evaluatable[list[Any]], func: EvaluatableFunction[F]
) -> Expression[list[F]]:
    return _list_expr(map_iterable(array, func, apply_ctx=True))


def filter_iterable[T](
    evalable_iterable: Evaluatable[Iterable[T]],
    func: EvaluatableFunction[bool],
    *,
    apply_ctx: bool = False,
) -> Expression[Iterable[T]]:
    def evaluate(ctx: Context) -> Iterable[T]:
        iterable = evaluate_value(evalable_iterable, ctx)
        return (
            item
            for item in iterable
            if evaluate_with_context(
                func,
                ctx=ctx.set_value(Value(item))
                if apply_ctx
                else Context(value=Value(item)),
            )[1]
        )

    return Expression(evaluate)


def filter_list[T](
    array: Evaluatable[list[T]], func: EvaluatableFunction[bool]
) -> Expression[list[T]]:
    return _list_expr(filter_iterable(array, func, apply_ctx=True))


def enumerate_iterable[T](
    array: Evaluatable[Iterable[T]], start: int = 0
) -> Expression[Iterable[tuple[int, T]]]:
    def evaluate(ctx: Context) -> Iterable[tuple[int, T]]:
        array_value = evaluate_value(array, ctx)
        return enumerate(array_value, start=start)

    return Expression(evaluate)


@dataclass(frozen=True, eq=False)
class SequenceExpression:
    pass
