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
}


class EvalBinOpSafe(ast.NodeVisitor):
    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type in OPERATORS:
            func, _ = OPERATORS[op_type]
            return func(left, right)
        else:
            raise NotImplementedError(f"Unsupported operator: {op_type}")

    def visit_Constant(self, node):
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        return node.value

    def generic_visit(self, node):
        raise NotImplementedError(f"Unsupported node type: {type(node)}")


def eval_binop_safe(expr: str | ast.Expression) -> Any:
    tree = ast.parse(expr, mode="eval")
    evaluator = EvalBinOpSafe()
    return evaluator.visit(tree.body)


expr = ast.parse("1+1+(2+2)", mode="eval")
print(eval_binop_safe(expr))
