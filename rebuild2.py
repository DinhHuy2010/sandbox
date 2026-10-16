import ast
import random
import string


def create_identifier(name=None):
    if name is None:
        c = random.choice(string.ascii_letters + "_")
        name = c + "".join(
            random.choice(string.ascii_letters + string.digits + "_") for _ in range(7)
        )
    return ast.Name(id=name, ctx=ast.Load())


# --- Expression Builders (Returns AST Expression / Name Nodes) ---


def make_var(name):
    """Creates a variable reference node (Load context)."""
    return ast.Name(id=name, ctx=ast.Load())


def make_num(value):
    """Creates a numeric literal node."""
    return ast.Constant(value=value)


def make_binop(op, left, right):
    """Creates a binary operation node (e.g., left + right)."""
    op_map = {
        "+": ast.Add(),
        "-": ast.Sub(),
        "*": ast.Mult(),
        "/": ast.Div(),
        ">": ast.Gt(),
        "<": ast.Lt(),
        "==": ast.Eq(),
    }

    # Binary math operations (+, -, etc.) use ast.BinOp
    if op in ("+", "-", "*", "/"):
        return ast.BinOp(left=left, op=op_map[op], right=right)
    # Comparison operations (>, <, ==) use ast.Compare
    return ast.Compare(left=left, ops=[op_map[op]], comparators=[right])


# --- Statement Builders (Returns AST Statement Nodes) ---


def make_assign(target_name, value_expr):
    """Creates an assignment statement: target = value."""
    return ast.Assign(
        targets=[ast.Name(id=target_name, ctx=ast.Store())], value=value_expr
    )


def make_return(expr):
    """Creates a return statement."""
    return ast.Return(value=expr)


def make_if(condition_expr, body_stmts, orelse_stmts=None):
    """Creates an if/else block."""
    return ast.If(test=condition_expr, body=body_stmts, orelse=orelse_stmts or [])


def make_for(target_name, iter_expr, body_stmts):
    """Creates a for loop."""
    return ast.For(
        target=ast.Name(id=target_name, ctx=ast.Store()),
        iter=iter_expr,
        body=body_stmts,
        orelse=[],
    )


def make_function(fn_name, arg_names, body_stmts):
    """Creates a full function definition AST node."""
    args_node = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg=name) for name in arg_names],
        kwonlyargs=[],
        kw_defaults=[],
        defaults=[],
        kwarg=None,
        vararg=None,
    )
    return ast.FunctionDef(
        name=fn_name, args=args_node, body=body_stmts, decorator_list=[], returns=None
    )


def make_call(fn_expr, arg_exprs, keywords=None):
    """Creates a function call expression node."""
    return ast.Call(func=fn_expr, args=arg_exprs, keywords=keywords or [])


def build_and_unparse(*ast_nodes):
    """Fills missing locations in the AST tree and converts to code string."""
    body = []
    for node in ast_nodes:
        ast.fix_missing_locations(node)
        # Wrap raw expressions into standalone expression statements
        if isinstance(node, ast.expr):
            node = ast.Expr(value=node)
        body.append(node)

    module = ast.Module(body=body, type_ignores=[])
    return ast.unparse(module)


time_mod = create_identifier()

print(
    build_and_unparse(
        make_assign(
            time_mod.id,
            make_call(
                ast.Name(id="__import__", ctx=ast.Load()), [ast.Constant(value="time")]
            ),
        ),
        make_call(
            ast.Attribute(value=time_mod, attr="sleep", ctx=ast.Load()),
            [ast.Constant(value=5)],
        ),
    )
)
