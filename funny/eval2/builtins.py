from __future__ import annotations

import builtins
import operator
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from frozendict import frozendict

from eval2.core import (
    Context,
    Evaluatable,
    EvaluatableFunction,
    EvaluatableOrValue,
    EvaluationResult,
    evaluate_value,
    execute_function,
    is_evaluatable,
)


def _build_binary_expression_method(
    method: str,
) -> Callable[[Evaluatable, EvaluatableOrValue], Expression]:
    import operator

    def _method(self: Evaluatable, other: EvaluatableOrValue) -> Expression:
        return binary_expression(
            getattr(operator, method), self, evaluatable_or_value(other)
        )

    return _method


def _build_unary_expression_method(method: str) -> Callable[[Evaluatable], Expression]:
    def _method(self: Evaluatable) -> Expression:
        return unary_expression(getattr(operator, method), self)

    return _method


class _BinaryExpressionMixin:
    __add__ = __radd__ = _build_binary_expression_method("add")
    __sub__ = __rsub__ = _build_binary_expression_method("sub")
    __mul__ = __rmul__ = _build_binary_expression_method("mul")
    __truediv__ = __rtruediv__ = _build_binary_expression_method("truediv")
    __floordiv__ = __rfloordiv__ = _build_binary_expression_method("floordiv")
    __mod__ = __rmod__ = _build_binary_expression_method("mod")
    __pow__ = __rpow__ = _build_binary_expression_method("pow")
    __and__ = __rand__ = _build_binary_expression_method("and_")
    __or__ = __ror__ = _build_binary_expression_method("or_")
    __xor__ = __rxor__ = _build_binary_expression_method("xor")
    __lshift__ = __rlshift__ = _build_binary_expression_method("lshift")
    __rshift__ = __rrshift__ = _build_binary_expression_method("rshift")
    __matmul__ = __rmatmul__ = _build_binary_expression_method("matmul")
    __eq__ = _build_binary_expression_method("eq")
    __ne__ = _build_binary_expression_method("ne")
    __lt__ = _build_binary_expression_method("lt")
    __le__ = _build_binary_expression_method("le")
    __gt__ = _build_binary_expression_method("gt")
    __ge__ = _build_binary_expression_method("ge")
    __neg__ = _build_unary_expression_method("neg")
    __pos__ = _build_unary_expression_method("pos")
    __abs__ = _build_unary_expression_method("abs")

    def __call__(self, *args, **kwds):
        return call(self, *args, **kwds)

    def __getattr__(self, attr: str) -> _getattr_expression:
        return _getattr_expression(self, attr)

    def __getitem__(self, key: Any) -> _getattr_expression:
        return _getattr_expression(self, key, getter=operator.getitem)


def contains(
    container: EvaluatableOrValue, item: EvaluatableOrValue
) -> Expression[bool]:
    return binary_expression(
        operator.contains, evaluatable_or_value(container), evaluatable_or_value(item)
    )


@dataclass(frozen=True, eq=False)
class _getattr_expression(_BinaryExpressionMixin):
    obj: Evaluatable[Any]
    attr: str
    getter: Callable[[Any, str], Any] = builtins.getattr

    def evaluate(self, ctx: Context[Any]) -> Any:
        obj_value = evaluate_value(self.obj, ctx)
        return self.getter(obj_value, self.attr)


@dataclass(frozen=True, eq=False)
class Value[T](_BinaryExpressionMixin):
    value: T

    def evaluate(self, ctx: Context) -> T:
        return self.value


@dataclass(frozen=True, eq=False)
class Reference(_BinaryExpressionMixin):
    name: str

    def evaluate(self, ctx: Context) -> Any:
        if self.name not in ctx.variables:
            raise ValueError(f"Variable {self.name!r} is not defined.")

        return evaluate_value(ctx.variables[self.name], ctx)


@dataclass(frozen=True, eq=False)
class Expression[R](_BinaryExpressionMixin):
    function: Callable[[Context[Any]], R]

    def evaluate(self, ctx: Context[Any]) -> R:
        return self.function(ctx)


@dataclass(frozen=True)
class ConditionalExpression[T, F](_BinaryExpressionMixin):
    condition: Evaluatable[bool]
    true_expr: Evaluatable[T]
    false_expr: Evaluatable[F]

    def evaluate(self, ctx: Context) -> T | F:
        if evaluate_value(self.condition, ctx):
            return evaluate_value(self.true_expr, ctx)
        else:
            return evaluate_value(self.false_expr, ctx)


def _hash_context(ctx: Context[Any]) -> int:
    out = set()
    for var_name, var_value in ctx.variables.items():
        try:
            h = hash(var_value)
        except TypeError:
            h = id(var_value)
        out.add((var_name, h))
    try:
        current_value_hash = hash(ctx.current_value)
    except TypeError:
        current_value_hash = id(ctx.current_value)
    return hash((current_value_hash, frozenset(out)))


@dataclass(frozen=True)
class CachedExpression[C](_BinaryExpressionMixin):
    expression: Evaluatable[C]
    cached_by_context: dict[int, C] = field(
        default_factory=dict, compare=False, hash=False
    )

    def evaluate(self, ctx: Context[Any]) -> C:
        ctx_hash = _hash_context(ctx)
        if ctx_hash in self.cached_by_context:
            print("HIT")
            return self.cached_by_context[ctx_hash]
        else:
            print("MISS")
            value = evaluate_value(self.expression, ctx)
            self.cached_by_context[ctx_hash] = value
            return value


def cache_expression[C](expression: Evaluatable[C]) -> CachedExpression[C]:
    return CachedExpression(expression)


def cache_evaluatable_function[C](
    func: EvaluatableFunction[C],
) -> EvaluatableFunction[C]:
    def evaluate(ctx: Context[Any]) -> EvaluationResult[C]:
        ctx_hash = _hash_context(ctx)
        if ctx_hash in func.cached_by_context:
            return ctx, func.cached_by_context[ctx_hash]
        else:
            ctx, value = execute_function(func, ctx)
            func.cached_by_context[ctx_hash] = value
            return ctx, value

    return evaluate


def conditional[T, F](
    condition: Evaluatable[bool],
    true_expr: Evaluatable[T],
    false_expr: Evaluatable[F],
) -> ConditionalExpression[T, F]:
    return ConditionalExpression(condition, true_expr, false_expr)


def while_loop(
    condition: Evaluatable[bool], func: EvaluatableFunction
) -> EvaluatableFunction:
    def evaluate(ctx: Context) -> EvaluationResult[Any]:
        while evaluate_value(condition, ctx):
            ctx = execute_function(func, ctx)
        return ctx, ctx.current_value

    return evaluate


def while_loop_expression(
    condition: Evaluatable[bool], func: EvaluatableFunction
) -> Expression:
    stmt = while_loop(condition, func)

    def evaluate(ctx: Context) -> Any:
        ctx, out_value = stmt(ctx)
        return evaluate_value(out_value, ctx)

    return Expression(evaluate)


def sequence(*funcs: EvaluatableFunction) -> EvaluatableFunction:
    def evaluate(ctx: Context) -> EvaluationResult[Any]:
        for func in funcs:
            ctx = execute_function(func, ctx)
        return ctx, ctx.current_value

    return evaluate


def conditional_statement(
    condition: Evaluatable[bool],
    true_func: EvaluatableFunction,
    false_func: EvaluatableFunction,
) -> EvaluatableFunction:
    def evaluate(ctx: Context) -> EvaluationResult[Any]:
        if evaluate_value(condition, ctx):
            ctx = execute_function(true_func, ctx)
        else:
            ctx = execute_function(false_func, ctx)
        return ctx, ctx.current_value

    return evaluate


def reference(name: str) -> Reference:
    return Reference(name)


def set_variables(**vars: Evaluatable[Any]) -> EvaluatableFunction:
    def evaluate(ctx: Context) -> EvaluationResult[Any]:
        ctx = ctx.add_variables(**vars)
        return ctx, ctx.current_value

    return evaluate


def delete_variables(*var_names: str) -> EvaluatableFunction:
    def evaluate(ctx: Context) -> EvaluationResult[Any]:
        new_variables = {k: v for k, v in ctx.variables.items() if k not in var_names}
        ctx = replace(ctx, variables=frozendict(new_variables))
        return ctx, ctx.current_value

    return evaluate


def use_variable(name: str) -> EvaluatableFunction:
    def evaluate(ctx: Context) -> EvaluationResult[Any]:
        value = ctx.get_variable(name)
        return ctx, value

    return evaluate


def use(value: Evaluatable[Any]) -> EvaluatableFunction:
    def evaluate(ctx: Context) -> EvaluationResult[Any]:
        return ctx, value

    return evaluate


def current_value() -> Expression[Any]:
    def evaluate(ctx: Context) -> Any:
        return evaluate_value(ctx.current_value, ctx)

    return Expression(evaluate)


def binary_expression[Left, Right, Output](
    op: Callable[[Left, Right], Output],
    left: Evaluatable[Left],
    right: Evaluatable[Right],
) -> Expression[Output]:
    def evaluate(ctx: Context) -> Output:
        left_value = evaluate_value(left, ctx)
        right_value = evaluate_value(right, ctx)
        return op(left_value, right_value)

    return Expression(evaluate)


def unary_expression[Operand, Output](
    op: Callable[[Operand], Output], operand: Evaluatable[Operand]
) -> Expression[Output]:
    def evaluate(ctx: Context) -> Output:
        operand_value = evaluate_value(operand, ctx)

        return op(operand_value)

    return Expression(evaluate)


def call(
    evaluatable_returning_function: EvaluatableOrValue[Callable[..., Any]],
    *args: EvaluatableOrValue[Any],
    **kwargs: EvaluatableOrValue[Any],
) -> Expression:

    def evaluate(ctx: Context) -> Any:
        evaluated_args = [
            evaluate_value(evaluatable_or_value(arg), ctx) for arg in args
        ]
        evaluated_kwargs = {
            key: evaluate_value(evaluatable_or_value(value), ctx)
            for key, value in kwargs.items()
        }
        func = evaluate_value(evaluatable_or_value(evaluatable_returning_function), ctx)
        return func(*evaluated_args, **evaluated_kwargs)

    return Expression(evaluate)


def evaluatable_or_value[T](value: EvaluatableOrValue[T]) -> Evaluatable[T]:
    if is_evaluatable(value):
        return value
    return Value(value)


def wrap_as_expression[**P, T](
    function: Callable[P, T] | Evaluatable[Callable[P, T]],
) -> Callable[P, Evaluatable[T]]:
    function = evaluatable_or_value(function)

    def wrapped(*args: P.args, **kwargs: P.kwargs) -> Evaluatable[T]:
        return call(function, *args, **kwargs)

    return wrapped


def wrap_as_evaluatable_function[**P, T](
    function: Callable[P, T] | Evaluatable[Callable[P, T]],
    *args: EvaluatableOrValue,
    **kwargs: EvaluatableOrValue,
) -> EvaluatableFunction[T]:
    function = evaluatable_or_value(function)

    def wrapped(ctx: Context) -> tuple[Context, Evaluatable[T]]:
        return ctx, call(function, *args, **kwargs)

    return wrapped
