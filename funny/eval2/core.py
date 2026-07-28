from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Protocol, Sequence, TypeIs, overload

from frozendict import frozendict

type VariablesContext = frozendict[str, Evaluatable[Any]]
type EvaluationResult[T] = tuple[Context, Evaluatable[T]]
type EvaluatableFunction[T] = Callable[[Context], EvaluationResult[T]]
type EvaluatableOrValue[T] = Evaluatable[T] | T


@dataclass(frozen=True)
class Context[T]:
    current_value: Evaluatable[T] = field(compare=False, hash=False)
    variables: VariablesContext = field(default_factory=frozendict)

    def set_variable(self, name: str, value: Evaluatable[Any]) -> Context[T]:
        return replace(self, variables=self.variables.set(name, value))

    def get_variable(self, name: str) -> Evaluatable[Any]:
        if name not in self.variables:
            raise ValueError(f"Variable {name!r} is not defined.")
        return self.variables[name]

    def add_variables(self, **vars: Evaluatable[Any]) -> Context[T]:
        ctx = self.variables
        for name, value in vars.items():
            ctx = ctx.set(name, value)
        return replace(self, variables=ctx)

    def set_value[R](self, value: Evaluatable[R]) -> Context[R]:
        return replace(self, current_value=value)


class Evaluatable[T](Protocol):
    def evaluate(self, ctx: Context[Any]) -> T: ...


class _InitialValue:
    def evaluate(self, ctx: Context[Any]) -> None:
        return None


class _BindingValue[T]:
    def __init__(self, value: Evaluatable[T], previous_value: Evaluatable[Any]):
        self.value = value
        self.previous_value = previous_value

    def evaluate(self, ctx: Context[Any]) -> T:
        bound_ctx = ctx.set_value(self.previous_value)
        return evaluate_value(self.value, bound_ctx)


def is_evaluatable(value: Any) -> TypeIs[Evaluatable[Any]]:
    return callable(getattr(value, "evaluate", None))


@overload
def evaluate_value[T](value: Evaluatable[T], ctx: Context | None = None) -> T: ...
@overload
def evaluate_value[T](
    value: list[Evaluatable[T]], ctx: Context | None = None
) -> list[T]: ...
@overload
def evaluate_value[K, T](
    value: dict[K, Evaluatable[T]], ctx: Context | None = None
) -> dict[K, T]: ...


def evaluate_value[K, T](
    value: Evaluatable[T] | list[Evaluatable[T]] | dict[K, Evaluatable[T]],
    ctx: Context | None = None,
) -> T | list[T] | dict[K, T]:
    if isinstance(value, list):
        return [evaluate_value(item, ctx) for item in value]

    if isinstance(value, dict):
        return {key: evaluate_value(item, ctx) for key, item in value.items()}

    if not is_evaluatable(value):
        raise ValueError(f"Value {value!r} is not evaluatable.")

    ctx = ctx or Context(variables=frozendict(), current_value=_InitialValue())

    while is_evaluatable(value):
        value = value.evaluate(ctx)

    return value


def bind_current_value[T](
    value: Evaluatable[T],
    previous_value: Evaluatable[Any],
) -> _BindingValue[T]:
    return _BindingValue(value, previous_value)


def execute_function[T](func: EvaluatableFunction[T], ctx: Context) -> Context[T]:
    previous_value = ctx.current_value
    ctx, new_value = func(ctx)

    return ctx.set_value(bind_current_value(new_value, previous_value))


def execute_functions(funcs: Sequence[EvaluatableFunction], ctx: Context) -> Context:
    for func in funcs:
        ctx = execute_function(func, ctx)
    return ctx


def evaluate_with_context(
    *functions: EvaluatableFunction, ctx: Context
) -> tuple[Context, Any]:
    ctx = execute_functions(functions, ctx)
    return ctx, evaluate_value(ctx.current_value, ctx)


def evaluate(*functions: EvaluatableFunction) -> Any:
    ctx: Context = Context(variables=frozendict(), current_value=_InitialValue())
    return evaluate_with_context(*functions, ctx=ctx)[1]
