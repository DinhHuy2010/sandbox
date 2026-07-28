# pyright: strict

"""ast_generator - random Python AST node generator."""

from __future__ import annotations

import ast
from contextlib import contextmanager
from random import Random
from typing import Callable, Iterator, TypeVar, cast

random = Random()

T = TypeVar("T")

MAX_LIST_SIZE = 5
MAX_DEPTH = 5
_depth = 0

_IDENTIFIER_CHARS = "abcdefghijklmnopqrstuvwxyz"
_CONSTANTS: list[object] = [None, True, False, 0, 1, -1, 3.14, "x", b"x", Ellipsis]


def generate_list(gen: Callable[[], T], n: int | None = None) -> list[T]:
    if n is not None:
        return [gen() for _ in range(n)]
    return [gen() for _ in range(random.randint(0, MAX_LIST_SIZE))]


def generate_non_empty_list(
    gen: Callable[[], T], max_size: int = MAX_LIST_SIZE
) -> list[T]:
    return [gen() for _ in range(random.randint(1, max_size))]


def generate_any(gens: list[Callable[[], T]]) -> T:
    gen = random.choice(gens)
    return gen()


@contextmanager
def recursion_guard() -> Iterator[None]:
    global _depth
    _depth += 1
    try:
        yield
    finally:
        _depth -= 1


def too_deep() -> bool:
    return _depth >= MAX_DEPTH


def generate_identifier(prefix: str = "x") -> str:
    name = "".join(random.choices(_IDENTIFIER_CHARS, k=random.randint(1, 8)))
    # Avoid keywords that are invalid identifiers in Name/arg positions.
    if name in {
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    }:
        return f"{prefix}_{name}"
    return f"{prefix}_{name}"


def generate_module_name() -> str:
    return ".".join(generate_identifier("m") for _ in range(random.randint(1, 3)))


def with_context(expr: ast.expr, ctx: ast.expr_context) -> ast.expr:
    """Return expr with a recursively adjusted context where that is meaningful."""
    match expr:  # type: ignore
        case ast.Name():
            expr.ctx = ctx
        case ast.Attribute():
            expr.ctx = ctx
            expr.value = with_context(expr.value, ast.Load())
        case ast.Subscript():
            expr.ctx = ctx
            expr.value = with_context(expr.value, ast.Load())
        case ast.Starred():
            expr.ctx = ctx
            expr.value = with_context(expr.value, ctx)
        case ast.List():
            expr.ctx = ctx
            expr.elts = [with_context(elt, ctx) for elt in expr.elts]
        case ast.Tuple():
            expr.ctx = ctx
            expr.elts = [with_context(elt, ctx) for elt in expr.elts]
    return expr


def generate_target() -> ast.expr:
    return with_context(
        generate_any(
            [
                generate_Name,
                generate_Attribute,
                generate_Subscript,
                generate_Tuple,
                generate_List,
            ]
        ),
        ast.Store(),
    )


def generate_optional_expr() -> ast.expr | None:
    return generate_any([generate_expr, lambda: None])


def generate_block() -> list[ast.stmt]:
    if too_deep():
        return [generate_Pass()]
    body = generate_list(generate_stmt)
    return body if body else [generate_Pass()]


def generate_operator() -> ast.operator:
    x = random.choice(
        [
            generate_Add,
            generate_BitAnd,
            generate_BitOr,
            generate_BitXor,
            generate_Div,
            generate_FloorDiv,
            generate_LShift,
            generate_MatMult,
            generate_Mod,
            generate_Mult,
            generate_Pow,
            generate_RShift,
            generate_Sub,
        ]
    )
    return x()


def generate_Add() -> ast.Add:
    return ast.Add()


def generate_BitAnd() -> ast.BitAnd:
    return ast.BitAnd()


def generate_BitOr() -> ast.BitOr:
    return ast.BitOr()


def generate_BitXor() -> ast.BitXor:
    return ast.BitXor()


def generate_Div() -> ast.Div:
    return ast.Div()


def generate_FloorDiv() -> ast.FloorDiv:
    return ast.FloorDiv()


def generate_LShift() -> ast.LShift:
    return ast.LShift()


def generate_MatMult() -> ast.MatMult:
    return ast.MatMult()


def generate_Mod() -> ast.Mod:
    return ast.Mod()


def generate_Mult() -> ast.Mult:
    return ast.Mult()


def generate_Pow() -> ast.Pow:
    return ast.Pow()


def generate_RShift() -> ast.RShift:
    return ast.RShift()


def generate_Sub() -> ast.Sub:
    return ast.Sub()


def generate_boolop() -> ast.boolop:
    x = random.choice([generate_And, generate_Or])
    return x()


def generate_And() -> ast.And:
    return ast.And()


def generate_Or() -> ast.Or:
    return ast.Or()


def generate_stmt() -> ast.stmt:
    if too_deep():
        return generate_any(
            [generate_Pass, generate_Expr, generate_Assign, generate_Return]
        )
    with recursion_guard():
        x = random.choice(
            [
                generate_AnnAssign,
                generate_Assert,
                generate_Assign,
                generate_AsyncFor,
                generate_AsyncFunctionDef,
                generate_AsyncWith,
                generate_AugAssign,
                generate_Break,
                generate_ClassDef,
                generate_Continue,
                generate_Delete,
                generate_Expr,
                generate_For,
                generate_FunctionDef,
                generate_Global,
                generate_If,
                generate_Import,
                generate_ImportFrom,
                generate_Match,
                generate_Nonlocal,
                generate_Pass,
                generate_Raise,
                generate_Return,
                generate_Try,
                generate_TryStar,
                generate_TypeAlias,
                generate_While,
                generate_With,
            ]
        )
        return x()


def generate_AnnAssign() -> ast.AnnAssign:
    target = generate_any([generate_Name, generate_Attribute, generate_Subscript])
    return ast.AnnAssign(
        target=cast(
            ast.Name | ast.Attribute | ast.Subscript, with_context(target, ast.Store())
        ),
        annotation=generate_expr(),
        value=generate_optional_expr(),
        simple=random.choice([0, 1]),
    )


def generate_Assert() -> ast.Assert:
    return ast.Assert(test=generate_expr(), msg=generate_optional_expr())


def generate_Assign() -> ast.Assign:
    return ast.Assign(
        targets=generate_non_empty_list(generate_target),
        value=generate_expr(),
        type_comment=random.choice([None, "# type: ignore"]),
    )


def generate_AsyncFor() -> ast.AsyncFor:
    return ast.AsyncFor(
        target=generate_target(),
        iter=generate_expr(),
        body=generate_block(),
        orelse=generate_list(generate_stmt),
        type_comment=random.choice([None, "# type: ignore"]),
    )


def generate_arg() -> ast.arg:
    return ast.arg(
        arg=generate_identifier("arg"),
        annotation=generate_optional_expr(),
        type_comment=random.choice([None, "# type: ignore"]),
    )


def generate_arguments() -> ast.arguments:
    posonlyargs = generate_list(generate_arg, random.randint(0, 2))
    args = generate_list(generate_arg, random.randint(0, 3))
    kwonlyargs = generate_list(generate_arg, random.randint(0, 2))
    kw_defaults = generate_list(
        lambda: generate_any([generate_expr, lambda: None]), n=len(kwonlyargs)
    )
    # Defaults apply to the last N positional args, so N must not exceed their count.
    positional_count = len(posonlyargs) + len(args)
    defaults = generate_list(generate_expr, random.randint(0, positional_count))
    return ast.arguments(
        posonlyargs=posonlyargs,
        args=args,
        vararg=generate_any([generate_arg, lambda: None]),
        kwonlyargs=kwonlyargs,
        kw_defaults=kw_defaults,
        kwarg=generate_any([generate_arg, lambda: None]),
        defaults=defaults,
    )


def generate_AsyncFunctionDef() -> ast.AsyncFunctionDef:
    return ast.AsyncFunctionDef(
        name=generate_identifier("async_fn"),
        args=generate_arguments(),
        body=generate_block(),
        decorator_list=generate_list(generate_expr),
        returns=generate_optional_expr(),
        type_comment=random.choice([None, "# type: ignore"]),
        type_params=generate_list(generate_type_param),
    )


def generate_AsyncWith() -> ast.AsyncWith:
    return ast.AsyncWith(
        items=generate_non_empty_list(generate_withitem),
        body=generate_block(),
        type_comment=random.choice([None, "# type: ignore"]),
    )


def generate_AugAssign() -> ast.AugAssign:
    return ast.AugAssign(
        target=generate_target(),  # type: ignore
        op=generate_operator(),
        value=generate_expr(),
    )


def generate_Break() -> ast.Break:
    return ast.Break()


def generate_ClassDef() -> ast.ClassDef:
    return ast.ClassDef(
        name=generate_identifier("Cls"),
        bases=generate_list(generate_expr),
        keywords=generate_list(generate_keyword),
        body=generate_block(),
        decorator_list=generate_list(generate_expr),
        type_params=generate_list(generate_type_param),
    )


def generate_Continue() -> ast.Continue:
    return ast.Continue()


def generate_Delete() -> ast.Delete:
    return ast.Delete(
        targets=generate_non_empty_list(
            lambda: with_context(generate_target(), ast.Del())
        )
    )


def generate_Expr() -> ast.Expr:
    return ast.Expr(value=generate_expr())


def generate_For() -> ast.For:
    return ast.For(
        target=generate_target(),
        iter=generate_expr(),
        body=generate_block(),
        orelse=generate_list(generate_stmt),
        type_comment=random.choice([None, "# type: ignore"]),
    )


def generate_FunctionDef() -> ast.FunctionDef:
    return ast.FunctionDef(
        name=generate_identifier("fn"),
        args=generate_arguments(),
        body=generate_block(),
        decorator_list=generate_list(generate_expr),
        returns=generate_optional_expr(),
        type_comment=random.choice([None, "# type: ignore"]),
        type_params=generate_list(generate_type_param),
    )


def generate_Global() -> ast.Global:
    return ast.Global(names=generate_non_empty_list(generate_identifier))


def generate_If() -> ast.If:
    return ast.If(
        test=generate_expr(), body=generate_block(), orelse=generate_list(generate_stmt)
    )


def generate_Import() -> ast.Import:
    return ast.Import(names=generate_non_empty_list(generate_alias))


def generate_ImportFrom() -> ast.ImportFrom:
    return ast.ImportFrom(
        module=random.choice([None, generate_module_name()]),
        names=generate_non_empty_list(generate_alias),
        level=random.randint(0, 3),
    )


def generate_Match() -> ast.Match:
    return ast.Match(
        subject=generate_expr(), cases=generate_non_empty_list(generate_match_case)
    )


def generate_match_case() -> ast.match_case:
    return ast.match_case(
        pattern=generate_pattern(),
        guard=generate_optional_expr(),
        body=generate_block(),
    )


def generate_Nonlocal() -> ast.Nonlocal:
    return ast.Nonlocal(names=generate_non_empty_list(generate_identifier))


def generate_Pass() -> ast.Pass:
    return ast.Pass()


def generate_Raise() -> ast.Raise:
    exc = generate_optional_expr()
    return ast.Raise(
        exc=exc, cause=generate_optional_expr() if exc is not None else None
    )


def generate_Return() -> ast.Return:
    return ast.Return(value=generate_optional_expr())


def generate_Try() -> ast.Try:
    handlers = generate_non_empty_list(generate_ExceptHandler)
    return ast.Try(
        body=generate_block(),
        handlers=handlers,
        orelse=generate_list(generate_stmt),
        finalbody=generate_list(generate_stmt),
    )


def generate_TryStar() -> ast.TryStar:
    return ast.TryStar(
        body=generate_block(),
        handlers=generate_non_empty_list(generate_ExceptHandler),
        orelse=generate_list(generate_stmt),
        finalbody=generate_list(generate_stmt),
    )


def generate_TypeAlias() -> ast.TypeAlias:
    return ast.TypeAlias(
        name=cast(ast.Name, with_context(generate_Name(), ast.Store())),
        type_params=generate_list(generate_type_param),
        value=generate_expr(),
    )


def generate_While() -> ast.While:
    return ast.While(
        test=generate_expr(), body=generate_block(), orelse=generate_list(generate_stmt)
    )


def generate_With() -> ast.With:
    return ast.With(
        items=generate_non_empty_list(generate_withitem),
        body=generate_block(),
        type_comment=random.choice([None, "# type: ignore"]),
    )


def generate_expr() -> ast.expr:
    if too_deep():
        return generate_any([generate_Constant, generate_Name])
    with recursion_guard():
        x = random.choice(
            [
                generate_Attribute,
                generate_Await,
                generate_BinOp,
                generate_BoolOp,
                generate_Call,
                generate_Compare,
                generate_Constant,
                generate_Dict,
                generate_DictComp,
                generate_FormattedValue,
                generate_GeneratorExp,
                generate_IfExp,
                generate_JoinedStr,
                generate_Lambda,
                generate_List,
                generate_ListComp,
                generate_Name,
                generate_NamedExpr,
                generate_Set,
                generate_SetComp,
                generate_Slice,
                generate_Starred,
                generate_Subscript,
                generate_Tuple,
                generate_UnaryOp,
                generate_Yield,
                generate_YieldFrom,
            ]
        )
        return x()


def generate_Attribute() -> ast.Attribute:
    return ast.Attribute(
        value=generate_expr(), attr=generate_identifier("attr"), ctx=ast.Load()
    )


def generate_Await() -> ast.Await:
    return ast.Await(value=generate_expr())


def generate_BinOp() -> ast.BinOp:
    return ast.BinOp(
        left=generate_expr(), op=generate_operator(), right=generate_expr()
    )


def generate_BoolOp() -> ast.BoolOp:
    return ast.BoolOp(
        op=generate_boolop(), values=generate_non_empty_list(generate_expr, max_size=3)
    )


def generate_Call() -> ast.Call:
    return ast.Call(
        func=generate_expr(),
        args=generate_list(generate_expr),
        keywords=generate_list(generate_keyword),
    )


def generate_Compare() -> ast.Compare:
    n = random.randint(1, 3)
    return ast.Compare(
        left=generate_expr(),
        ops=generate_list(generate_cmpop, n=n),
        comparators=generate_list(generate_expr, n=n),
    )


def generate_Constant() -> ast.Constant:
    return ast.Constant(value=random.choice(_CONSTANTS), kind=None)  # type: ignore


def generate_Dict() -> ast.Dict:
    n = random.randint(0, MAX_LIST_SIZE)
    return ast.Dict(
        keys=generate_list(generate_expr, n=n), values=generate_list(generate_expr, n=n)
    )


def generate_DictComp() -> ast.DictComp:
    return ast.DictComp(
        key=generate_expr(),
        value=generate_expr(),
        generators=generate_non_empty_list(generate_comprehension),
    )


def generate_FormattedValue() -> ast.FormattedValue:
    return ast.FormattedValue(
        value=generate_expr(),
        conversion=random.choice([-1, 115, 114, 97]),
        format_spec=generate_any([generate_JoinedStr, lambda: None]),
    )


def generate_GeneratorExp() -> ast.GeneratorExp:
    return ast.GeneratorExp(
        elt=generate_expr(), generators=generate_non_empty_list(generate_comprehension)
    )


def generate_IfExp() -> ast.IfExp:
    return ast.IfExp(test=generate_expr(), body=generate_expr(), orelse=generate_expr())


def generate_JoinedStr() -> ast.JoinedStr:
    values = generate_non_empty_list(
        lambda: generate_any([generate_FormattedValue, generate_string_constant]),
        max_size=3,
    )
    return ast.JoinedStr(values=values)  # type: ignore


def generate_Lambda() -> ast.Lambda:
    return ast.Lambda(args=generate_arguments(), body=generate_expr())


def generate_List() -> ast.List:
    return ast.List(elts=generate_list(generate_expr), ctx=ast.Load())


def generate_ListComp() -> ast.ListComp:
    return ast.ListComp(
        elt=generate_expr(), generators=generate_non_empty_list(generate_comprehension)
    )


def generate_Name() -> ast.Name:
    return ast.Name(id=generate_identifier("x"), ctx=ast.Load())


def generate_NamedExpr() -> ast.NamedExpr:
    return ast.NamedExpr(
        target=with_context(generate_Name(), ast.Store()),  # type: ignore
        value=generate_expr(),
    )


def generate_Set() -> ast.Set:
    return ast.Set(elts=generate_list(generate_expr))


def generate_SetComp() -> ast.SetComp:
    return ast.SetComp(
        elt=generate_expr(), generators=generate_non_empty_list(generate_comprehension)
    )


def generate_Slice() -> ast.Slice:
    return ast.Slice(
        lower=generate_optional_expr(),
        upper=generate_optional_expr(),
        step=generate_optional_expr(),
    )


def generate_Starred() -> ast.Starred:
    return ast.Starred(value=generate_expr(), ctx=ast.Load())


def generate_Subscript() -> ast.Subscript:
    return ast.Subscript(
        value=generate_expr(),
        slice=generate_any([generate_expr, generate_Slice]),
        ctx=ast.Load(),
    )


def generate_Tuple() -> ast.Tuple:
    return ast.Tuple(elts=generate_list(generate_expr), ctx=ast.Load())


def generate_UnaryOp() -> ast.UnaryOp:
    return ast.UnaryOp(op=generate_unaryop(), operand=generate_expr())


def generate_Yield() -> ast.Yield:
    return ast.Yield(value=generate_optional_expr())


def generate_YieldFrom() -> ast.YieldFrom:
    return ast.YieldFrom(value=generate_expr())


def generate_string_constant() -> ast.Constant:
    return ast.Constant(value=random.choice(["", "x", "hello", "{}"]), kind=None)


def generate_expr_context() -> ast.expr_context:
    x = random.choice([generate_Del, generate_Load, generate_Store])
    return x()


def generate_Del() -> ast.Del:
    return ast.Del()


def generate_Load() -> ast.Load:
    return ast.Load()


def generate_Store() -> ast.Store:
    return ast.Store()


def generate_cmpop() -> ast.cmpop:
    x = random.choice(
        [
            generate_Eq,
            generate_Gt,
            generate_GtE,
            generate_In,
            generate_Is,
            generate_IsNot,
            generate_Lt,
            generate_LtE,
            generate_NotEq,
            generate_NotIn,
        ]
    )
    return x()


def generate_Eq() -> ast.Eq:
    return ast.Eq()


def generate_Gt() -> ast.Gt:
    return ast.Gt()


def generate_GtE() -> ast.GtE:
    return ast.GtE()


def generate_In() -> ast.In:
    return ast.In()


def generate_Is() -> ast.Is:
    return ast.Is()


def generate_IsNot() -> ast.IsNot:
    return ast.IsNot()


def generate_Lt() -> ast.Lt:
    return ast.Lt()


def generate_LtE() -> ast.LtE:
    return ast.LtE()


def generate_NotEq() -> ast.NotEq:
    return ast.NotEq()


def generate_NotIn() -> ast.NotIn:
    return ast.NotIn()


def generate_excepthandler() -> ast.excepthandler:
    x = random.choice([generate_ExceptHandler])
    return x()


def generate_ExceptHandler() -> ast.ExceptHandler:
    return ast.ExceptHandler(
        type=generate_optional_expr(),
        name=random.choice([None, generate_identifier("exc")]),
        body=generate_block(),
    )


def generate_mod() -> ast.mod:
    x = random.choice(
        [
            generate_Expression,
            generate_FunctionType,
            generate_Interactive,
            generate_Module,
        ]
    )
    return x()


def generate_Expression() -> ast.Expression:
    return ast.Expression(body=generate_expr())


def generate_FunctionType() -> ast.FunctionType:
    return ast.FunctionType(
        argtypes=generate_list(generate_expr), returns=generate_expr()
    )


def generate_Interactive() -> ast.Interactive:
    return ast.Interactive(body=generate_block())


def generate_Module() -> ast.Module:
    return ast.Module(
        body=generate_block(),
        type_ignores=generate_list(generate_type_ignore),  # type: ignore
    )


def generate_unaryop() -> ast.unaryop:
    x = random.choice([generate_Invert, generate_Not, generate_UAdd, generate_USub])
    return x()


def generate_Invert() -> ast.Invert:
    return ast.Invert()


def generate_Not() -> ast.Not:
    return ast.Not()


def generate_UAdd() -> ast.UAdd:
    return ast.UAdd()


def generate_USub() -> ast.USub:
    return ast.USub()


def generate_pattern() -> ast.pattern:
    if too_deep():
        return generate_any(
            [generate_MatchAs, generate_MatchSingleton, generate_MatchValue]
        )
    with recursion_guard():
        x = random.choice(
            [
                generate_MatchAs,
                generate_MatchClass,
                generate_MatchMapping,
                generate_MatchOr,
                generate_MatchSequence,
                generate_MatchSingleton,
                generate_MatchStar,
                generate_MatchValue,
            ]
        )
        return x()


def generate_MatchAs() -> ast.MatchAs:
    if random.choice([True, False]):
        return ast.MatchAs(pattern=generate_pattern(), name=generate_identifier("case"))
    return ast.MatchAs(
        pattern=None, name=random.choice([None, generate_identifier("case")])
    )


def generate_MatchClass() -> ast.MatchClass:
    n = random.randint(0, MAX_LIST_SIZE)
    return ast.MatchClass(
        cls=generate_expr(),
        patterns=generate_list(generate_pattern),
        kwd_attrs=generate_list(generate_identifier, n=n),
        kwd_patterns=generate_list(generate_pattern, n=n),
    )


def generate_MatchMapping() -> ast.MatchMapping:
    n = random.randint(0, MAX_LIST_SIZE)
    return ast.MatchMapping(
        keys=generate_list(generate_expr, n=n),
        patterns=generate_list(generate_pattern, n=n),
        rest=random.choice([None, generate_identifier("rest")]),
    )


def generate_MatchOr() -> ast.MatchOr:
    return ast.MatchOr(patterns=generate_non_empty_list(generate_pattern, max_size=3))


def generate_MatchSequence() -> ast.MatchSequence:
    return ast.MatchSequence(patterns=generate_list(generate_pattern))


def generate_MatchSingleton() -> ast.MatchSingleton:
    return ast.MatchSingleton(value=random.choice([None, True, False]))


def generate_MatchStar() -> ast.MatchStar:
    return ast.MatchStar(name=random.choice([None, generate_identifier("star")]))


def generate_MatchValue() -> ast.MatchValue:
    return ast.MatchValue(value=generate_any([generate_Constant, generate_Attribute]))


def generate_type_param() -> ast.type_param:
    x = random.choice([generate_ParamSpec, generate_TypeVar, generate_TypeVarTuple])
    return x()


def generate_ParamSpec() -> ast.ParamSpec:
    return ast.ParamSpec(name=generate_identifier("P"))


def generate_TypeVar() -> ast.TypeVar:
    return ast.TypeVar(name=generate_identifier("T"), bound=generate_optional_expr())


def generate_TypeVarTuple() -> ast.TypeVarTuple:
    return ast.TypeVarTuple(name=generate_identifier("Ts"))


def generate_type_ignore() -> ast.type_ignore:
    x = random.choice([generate_TypeIgnore])
    return x()


def generate_TypeIgnore() -> ast.TypeIgnore:
    return ast.TypeIgnore(
        lineno=random.randint(1, 999), tag=random.choice(["", "type: ignore"])
    )


def generate_alias() -> ast.alias:
    return ast.alias(
        name=generate_module_name(),
        asname=random.choice([None, generate_identifier("as")]),
    )


def generate_keyword() -> ast.keyword:
    return ast.keyword(
        arg=random.choice([None, generate_identifier("kw")]), value=generate_expr()
    )


def generate_withitem() -> ast.withitem:
    return ast.withitem(
        context_expr=generate_expr(),
        optional_vars=generate_any([lambda: generate_target(), lambda: None]),
    )


def generate_comprehension() -> ast.comprehension:
    return ast.comprehension(
        target=generate_target(),
        iter=generate_expr(),
        ifs=generate_list(generate_expr),
        is_async=random.choice([0, 1]),
    )


def sample_source() -> str:
    """Generate a random module and unparse it for quick visual inspection."""
    tree = generate_Module()
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


if __name__ == "__main__":
    print(sample_source())
