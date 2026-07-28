from dataclasses import dataclass
from typing import Any, Callable, Protocol
from frozendict import frozendict


type Context = frozendict[str, Evaluatable]
type EvalData = tuple[Context, Evaluatable]
type EvalFunction = Callable[[Context, Evaluatable], EvalData]


class Evaluatable[T](Protocol):
    def evaluate(self, ctx: Context) -> T:
        """
        Evaluate the value in the given context.

        This method should be implemented by subclasses to define how the value is evaluated.
        """


@dataclass
class Reference(Evaluatable[Any]):
    """
    A class to represent a reference to a variable in the evaluation context.
    """

    name: str

    def evaluate(self, ctx):
        try:
            out = evaluate_value(ctx[self.name], ctx)
        except KeyError:
            raise ValueError(f"Variable '{self.name}' is not defined in the context.")
        else:
            if is_evaluatable(out):
                return evaluate_value(out, ctx)
            return out


@dataclass
class Value(Evaluatable[Any]):
    """
    A class to represent a concrete value in the evaluation context.
    """

    value: Any

    def evaluate(self, ctx):
        return self.value


class ExpressionForm(Evaluatable[Any]):
    """
    A class to represent a value that is computed from a function during evaluation.
    """

    def __init__(self, func: Callable[[Context], Any]):
        self.func = func

    def evaluate(self, ctx):
        return self.func(ctx)


class Array[R](Evaluatable[list[R]]):
    """
    A class to represent an array of evaluatable values.
    """

    def __init__(self, *values: Evaluatable[R]):
        self.values = values

    def evaluate(self, ctx):
        return [evaluate_value(value, ctx) for value in self.values]


def map_array[R, E](
    func: Callable[[R], E], array: Evaluatable[list[R]] | None = None
) -> EvalFunction:
    """
    Create a new Array by applying a function to each element of an existing Array.

    This function takes a callable and an Array, and returns a new Array where each element
    is the result of applying the function to the corresponding element in the original Array.
    """

    def inner(ctx: Context, value: Evaluatable) -> EvalData:
        value = evaluate_value(array or value, ctx)
        if not isinstance(value, list):
            raise ValueError(
                f"Expected a list for mapping, but got {type(value).__name__}."
            )
        return ctx, Array(*(ExpressionForm(lambda ctx, v=v: func(v)) for v in value))

    return inner


def reference(name: str) -> Reference:
    """
    Create a Reference object for a given variable name.
    """
    return Reference(name)


def is_evaluatable(obj: Any) -> bool:
    """
    Check if an object is evaluatable.

    An object is considered evaluatable if it has an 'evaluate' method that is callable.
    """
    return callable(getattr(obj, "evaluate", None))


def evaluate_value(e: Evaluatable, ctx: Context | None = None) -> Any:
    evaluate = getattr(e, "evaluate", None)
    if not callable(evaluate):
        raise ValueError(f"Object {type(e).__name__!r} is not evaluatable.")

    if ctx is None:
        ctx = frozendict()
    try:
        out = evaluate(ctx)
    except Exception as ex:
        raise ValueError(f"Error evaluating {type(e).__name__!r}: {ex}") from ex
    return out


def evaluate(
    *functions: EvalFunction, initial: Evaluatable = Value(None), **ctx: Any
) -> EvalData:
    """
    Evaluate a sequence of functions with an initial empty context and value.

    Each function should accept a context and a value, and return a new context and value.
    The final context and value are returned after all functions have been applied.
    """
    ctx, value = frozendict(**ctx), initial

    for function in functions:
        ctx, value = function(ctx, value)

    try:
        value = evaluate_value(value, ctx)
    except ValueError:
        raise ValueError("The final value is not an evaluatable.")

    return ctx, value


def define_variables(**vars: Evaluatable) -> EvalFunction:
    """
    Create an evaluation function that defines variables in the context.

    This function takes keyword arguments representing variable names and their values,
    and returns a function that adds these variables to the context.
    """

    def inner(ctx: Context, value: Evaluatable) -> EvalData:
        new_ctx = ctx
        for key, val in vars.items():
            new_ctx = new_ctx.set(key, val)
        return new_ctx, value

    return inner


class BinaryOperation(Evaluatable):
    """
    A class to represent a binary operation between two evaluatable values.
    """

    def __init__(
        self, op: Callable[[Any, Any], Any], left: Evaluatable, right: Evaluatable
    ):
        self.op = op
        self.left = left
        self.right = right

    def evaluate(self, ctx: Context) -> Any:
        left_value = evaluate_value(self.left, ctx)
        right_value = evaluate_value(self.right, ctx)
        return self.op(left_value, right_value)


class UnaryOperation(Evaluatable):
    """
    A class to represent a unary operation on an evaluatable value.
    """

    def __init__(self, op: Callable[[Any], Any], operand: Evaluatable | None = None):
        self.op = op
        self.operand = operand

    def evaluate(self, ctx: Context) -> Any:
        operand_value = evaluate_value(self.operand, ctx) if self.operand else None
        return self.op(operand_value)


def output(
    value: Evaluatable | None = None, *, end: str = "\n", discard_none: bool = True
) -> EvalFunction:
    """
    Create an evaluation function that outputs the evaluated value.

    This function takes an evaluatable value and returns a function that evaluates it
    and prints the result.

    This function will recursively evaluate the provided value and print it to the standard output.
    """

    def inner(ctx: Context, _: Evaluatable) -> EvalData:
        evaluated_value = evaluate_value(value or _, ctx)
        if discard_none and evaluated_value is None:
            return ctx, Value(None)
        print(evaluated_value, end=end)
        return ctx, Value(evaluated_value)

    return inner


def discard(*, keep_evaluating: bool = False) -> EvalFunction:
    """
    Create an evaluation function that discards the evaluated value.

    This function returns a function that evaluates the provided value
    and discards it, returning an evaluatable representing None as the new value.
    """

    def inner(ctx: Context, value: Evaluatable) -> EvalData:
        if keep_evaluating:
            evaluate_value(value, ctx)  # Evaluate the value but discard it

        return ctx, Value(
            None
        )  # Return an evaluatable representing None as the new value

    return inner


def use(value: Evaluatable) -> EvalFunction:
    """
    Create an evaluation function that uses the evaluated value.

    This function returns a function that evaluates the provided value
    and returns it as the new value in the evaluation context.
    """

    def inner(ctx: Context, _: Evaluatable) -> EvalData:
        # evaluated_value = evaluate_value(value, ctx)
        return ctx, value

    return inner


def run(*functions: EvalFunction) -> Any:
    """
    Run a sequence of evaluation functions and return the final value.

    This function evaluates the provided functions in order and returns the final value.
    """
    _, value = evaluate(*functions)
    # if value is not None:
    #     print(value)
    return value


run(
    define_variables(x=Value(42), y=Value("Hello")),
    define_variables(
        out=BinaryOperation(lambda a, b: f"{b}, {a}!", reference("x"), reference("y")),
    ),
    define_variables(arr=Array(Value(1), Value(2), Value(3))),
    map_array(lambda x: x * 2, reference("arr")),
    output(),
)
