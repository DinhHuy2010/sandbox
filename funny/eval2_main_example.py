from __future__ import annotations

from eval2.builtins import while_loop
from eval2.core import Context, current_value, evaluate_with_context, Value
from eval2.core import binary_expression as binop
from eval2.io.path import PathExpression


def ask_path(ctx):
    x = input("Please enter a path: ")
    return ctx, PathExpression(Value(x))

def read_data(ctx):
    value = ctx.current_value
    if not isinstance(value, PathExpression):
        raise ValueError(f"Value {value!r} is not a PathExpression.")
    return ctx, value.read_text()


p = evaluate_with_context(ask_path, read_data, ctx=Context(Value(None)))
print(p)

# def read_out(ctx):
#     value = ctx.current_value
#     if not isinstance(value, PathExpression):
#         raise ValueError(f"Value {value!r} is not a PathExpression.")
#     return ctx, value.read()


# def lt(a, b):
#     return a < b


# def add(a, b):
#     return a + b


# def body(ctx):
#     current = ctx.current_value
#     new_value = binop(add, current, Value(1))
#     return ctx, new_value


# stmt = while_loop(
#     condition=binop(lt, current_value(), Value(10)),
#     func=body,
# )
# ctx, p = evaluate_with_context(stmt, ctx=Context(variables={}, current_value=Value(0)))
# print(p)
