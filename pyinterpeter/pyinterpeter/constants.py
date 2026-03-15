import ast
import operator
from typing import Any

OPERATORS: dict[type[ast.AST], Any] = {
    ast.Add: (operator.add, "__add__"),
    ast.Sub: (operator.sub, "__sub__"),
    ast.Mult: (operator.mul, "__mul__"),
    ast.Div: (operator.truediv, "__truediv__"),
    ast.Mod: (operator.mod, "__mod__"),
    ast.Pow: (operator.pow, "__pow__"),
    ast.LShift: (operator.lshift, "__lshift__"),
    ast.RShift: (operator.rshift, "__rshift__"),
    ast.BitOr: (operator.or_, "__or__"),
    ast.BitXor: (operator.xor, "__xor__"),
    ast.BitAnd: (operator.and_, "__and__"),
    ast.FloorDiv: (operator.floordiv, "__floordiv__"),
    ast.MatMult: (operator.matmul, "__matmul__"),
    ast.Gt: (operator.gt, "__gt__"),
    ast.Lt: (operator.lt, "__lt__"),
    ast.GtE: (operator.ge, "__ge__"),
    ast.LtE: (operator.le, "__le__"),
    ast.Eq: (operator.eq, "__eq__"),
    ast.NotEq: (operator.ne, "__ne__"),
    ast.In: (operator.contains, "__contains__"),
}
OPNAME_TO_FUNC = {n: f for f, n in OPERATORS.values()}
