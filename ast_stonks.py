# import ast

# fndef = ast.FunctionDef(
#     name="stonks",
#     args=ast.arguments(
#         posonlyargs=[],
#         args=[ast.arg(arg="self", annotation=None)],
#         kwonlyargs=[
#             ast.arg(arg="N", annotation=None),
#         ],
#         kw_defaults=[None],
#         defaults=[],
#     ),
#     body=[
#         ast.Return(
#             value=ast.BinOp(
#                 left=ast.Name(id="stonks", ctx=ast.Load()),
#                 op=ast.Add(),
#                 right=ast.Constant(value=100),
#             )
#         )
#     ],
#     decorator_list=[],
#     type_params=[],
#     lineno=1,
# )
# print(ast.unparse(fndef))

import ast
import random
from collections import deque

from pydantic import JsonValue


def _generate_lambda_sum_ast() -> ast.Lambda:
    seq_var = "".join(
        [random.choice("abcdefghijklmnopqrstuvwxyz")]
        + random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=7)
    )
    a_var = "".join(
        [random.choice("abcdefghijklmnopqrstuvwxyz")]
        + random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=7)
    )
    b_var = "".join(
        [random.choice("abcdefghijklmnopqrstuvwxyz")]
        + random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=7)
    )
    return ast.Lambda(
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=seq_var, annotation=None)],
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
        ),
        body=ast.Call(
            func=ast.Attribute(
                value=ast.Call(
                    func=ast.Name(id="__import__", ctx=ast.Load()),
                    args=[ast.Constant(value="functools")],
                    keywords=[],
                ),
                attr="reduce",
                ctx=ast.Load(),
            ),
            args=[
                ast.Lambda(
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[
                            ast.arg(arg=a_var, annotation=None),
                            ast.arg(arg=b_var, annotation=None),
                        ],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[],
                    ),
                    body=ast.BinOp(
                        left=ast.Name(id=a_var, ctx=ast.Load()),
                        op=ast.Add(),
                        right=ast.Name(id=b_var, ctx=ast.Load()),
                    ),
                ),
                ast.Name(id=seq_var, ctx=ast.Load()),
                ast.Constant(value=0),
            ],
            keywords=[],
        ),
    )


def _generate_binop_add(target: int, max_seq: int | None = None) -> ast.BinOp:
    def find_seq(n: int) -> list[int]:
        seq: list[int] = []
        while n > 0:
            if max_seq is not None and len(seq) >= max_seq - 1:
                seq.append(n)
                break
            part = random.randint(1, max(1, n // 2))
            seq.append(part)
            n -= part
        return seq

    parts = find_seq(target)
    expr: ast.expr = (
        _generate_binop_add(parts[0])
        if len(parts) > 1
        else ast.Constant(value=parts[0])
    )
    stacks = deque(parts[1:])
    while stacks:
        part = stacks.popleft()
        if random.random() < 0.2 and len(stacks) >= 1:
            ot = random.sample(stacks, min(len(stacks), len(stacks) // 5))
            if not ot:
                right = ast.Constant(value=part)
                expr = ast.BinOp(
                    left=expr,
                    op=ast.Add(),
                    right=right,
                )
                continue
            call = ast.Call(
                func=ast.Name(id="sum", ctx=ast.Load())
                if random.random() > 0.5
                else _generate_lambda_sum_ast(),
                args=[
                    ast.Tuple(
                        elts=[_generate_binop_add(p) for p in ot],
                        ctx=ast.Load(),
                    )
                ],
                keywords=[],
            )
            for p in ot:
                stacks.remove(p)
            right = ast.BinOp(
                left=ast.Constant(value=part),
                op=ast.Add(),
                right=call,
            )
        elif random.random() < 0.3 and part >= 2:
            right = _generate_binop_add(part, max_seq=3)
        else:
            right = ast.Constant(value=part)
        expr = ast.BinOp(
            left=expr,
            op=ast.Add(),
            right=right,
        )
    if isinstance(expr, ast.Constant):
        expr = ast.BinOp(
            left=expr,
            op=ast.Add(),
            right=ast.Constant(value=0),
        )
    return expr


def generate_obf_constants(const: ast.Constant):
    if isinstance(const.value, int):
        value = const.value
        obf_expr = _generate_binop_add(value)
    else:
        obf_expr = const  # No obfuscation for non-integers for now
    print("Obfuscated Expression:", ast.unparse(obf_expr))
    return obf_expr


def _eval_json_to_ast(js: JsonValue) -> ast.expr:
    print("Evaluating:", js)
    if isinstance(js, (str, int, float, bool, type(None))):
        return ast.Constant(value=js)
    elif isinstance(js, dict):
        return ast.Dict(
            keys=[ast.Constant(k) for k in js.keys()],
            values=[_eval_json_to_ast(v) for v in js.values()],
        )
    elif isinstance(js, list):  # type: ignore
        return ast.List(elts=[_eval_json_to_ast(e) for e in js], ctx=ast.Load())
    else:
        raise ValueError(f"Unsupported JSON value: {js}")


def pyjson_to_ast(js: JsonValue) -> ast.Expression:
    return ast.Expression(body=_eval_json_to_ast(js))


# j: JsonValue = {
#     "name": "Alice",
#     "age": 30,
#     "is_student": False,
#     "courses": ["Math", "Science"],
#     "address": {"city": "Wonderland", "zip": "12345"},
#     "scores": [95, 88, 76],
#     "misc": None,
# }

# print(ast.unparse(pyjson_to_ast(j)))
t = 9348
for _ in range(5):
    p = ast.fix_missing_locations(
        ast.Expression(body=generate_obf_constants(ast.Constant(t)))
    )
    assert eval(compile(p, filename="<ast>", mode="eval")) == t
