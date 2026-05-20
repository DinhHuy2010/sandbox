# pyright: strict

import ast
from random import Random
from typing import Callable

random = Random()
MAX_LIST_SIZE = 300


def generate_list[T](gen: Callable[[], T], n: int | None = None) -> list[T]:
    if n is not None:
        return [gen() for _ in range(n)]
    return [gen() for _ in range(random.randint(2, MAX_LIST_SIZE))]


def generate_any[T](gens: list[Callable[[], T]]) -> T:
    gen = random.choice(gens)
    return gen()


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
    # raise NotImplementedError()
    return ast.AnnAssign(
        target=generate_any(
            [
                generate_Attribute,
                generate_Name,
                generate_Subscript,
            ]
        ),
        annotation=generate_expr(),
        value=generate_expr(),
        simple=random.choice([0, 1]),
    )


def generate_Assert() -> ast.Assert:
    # raise NotImplementedError()
    return ast.Assert(
        test=generate_expr(),
        msg=generate_any([generate_expr, lambda: None]),
    )


def generate_Assign() -> ast.Assign:
    return ast.Assign(
        targets=generate_list(generate_expr),
        value=generate_expr(),
        type_comment=random.choice([None, "# type: ignore"]),
    )


def generate_AsyncFor() -> ast.AsyncFor:
    # raise NotImplementedError()
    return ast.AsyncFor(
        target=generate_expr(),
        iter=generate_expr(),
        body=generate_list(generate_stmt),
        orelse=generate_list(generate_stmt),
    )


def generate_arg() -> ast.arg:
    raise NotImplementedError()


def generate_AsyncFunctionDef() -> ast.AsyncFunctionDef:
    # raise NotImplementedError()
    name = "".join(
        random.choices("abcdefghijklmnopqrstuvwxyz", k=random.randint(1, 10))
    )
    posargs: list[ast.arg] = generate_list(generate_arg)
    args: list[ast.arg] = generate_list(generate_arg)
    kwonlyargs: list[ast.arg] = generate_list(generate_arg)
    kw_defaults: list[ast.expr | None] = generate_list(
        lambda: generate_any([generate_expr, lambda: None]),
        n=len(kwonlyargs),
    )
    body = generate_list(generate_stmt)
    decorator_list = generate_list(generate_expr)
    returns = generate_any([generate_expr, lambda: None])
    type_comment = random.choice([None, "# type: ignore"])
    type_params = generate_list(generate_type_param)
    arguments = ast.arguments(posargs, args, None, kwonlyargs, kw_defaults, None, [])
    return ast.AsyncFunctionDef(
        name=name,
        args=arguments,
        body=body,
        decorator_list=decorator_list,
        returns=returns,
        type_comment=type_comment,
        type_params=type_params,
    )


def generate_AsyncWith() -> ast.AsyncWith:
    raise NotImplementedError()


def generate_AugAssign() -> ast.AugAssign:
    raise NotImplementedError()


def generate_Break() -> ast.Break:
    raise NotImplementedError()


def generate_ClassDef() -> ast.ClassDef:
    raise NotImplementedError()


def generate_Continue() -> ast.Continue:
    raise NotImplementedError()


def generate_Delete() -> ast.Delete:
    raise NotImplementedError()


def generate_Expr() -> ast.Expr:
    raise NotImplementedError()


def generate_For() -> ast.For:
    raise NotImplementedError()


def generate_FunctionDef() -> ast.FunctionDef:
    raise NotImplementedError()


def generate_Global() -> ast.Global:
    raise NotImplementedError()


def generate_If() -> ast.If:
    raise NotImplementedError()


def generate_Import() -> ast.Import:
    raise NotImplementedError()


def generate_ImportFrom() -> ast.ImportFrom:
    raise NotImplementedError()


def generate_Match() -> ast.Match:
    raise NotImplementedError()


def generate_Nonlocal() -> ast.Nonlocal:
    raise NotImplementedError()


def generate_Pass() -> ast.Pass:
    raise NotImplementedError()


def generate_Raise() -> ast.Raise:
    raise NotImplementedError()


def generate_Return() -> ast.Return:
    raise NotImplementedError()


def generate_Try() -> ast.Try:
    raise NotImplementedError()


def generate_TryStar() -> ast.TryStar:
    raise NotImplementedError()


def generate_TypeAlias() -> ast.TypeAlias:
    raise NotImplementedError()


def generate_While() -> ast.While:
    raise NotImplementedError()


def generate_With() -> ast.With:
    raise NotImplementedError()


def generate_expr() -> ast.expr:
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
    raise NotImplementedError()


def generate_Await() -> ast.Await:
    raise NotImplementedError()


def generate_BinOp() -> ast.BinOp:
    raise NotImplementedError()


def generate_BoolOp() -> ast.BoolOp:
    raise NotImplementedError()


def generate_Call() -> ast.Call:
    raise NotImplementedError()


def generate_Compare() -> ast.Compare:
    raise NotImplementedError()


def generate_Constant() -> ast.Constant:
    raise NotImplementedError()


def generate_Dict() -> ast.Dict:
    raise NotImplementedError()


def generate_DictComp() -> ast.DictComp:
    raise NotImplementedError()


def generate_FormattedValue() -> ast.FormattedValue:
    raise NotImplementedError()


def generate_GeneratorExp() -> ast.GeneratorExp:
    raise NotImplementedError()


def generate_IfExp() -> ast.IfExp:
    raise NotImplementedError()


def generate_JoinedStr() -> ast.JoinedStr:
    raise NotImplementedError()


def generate_Lambda() -> ast.Lambda:
    raise NotImplementedError()


def generate_List() -> ast.List:
    raise NotImplementedError()


def generate_ListComp() -> ast.ListComp:
    raise NotImplementedError()


def generate_Name() -> ast.Name:
    raise NotImplementedError()


def generate_NamedExpr() -> ast.NamedExpr:
    raise NotImplementedError()


def generate_Set() -> ast.Set:
    raise NotImplementedError()


def generate_SetComp() -> ast.SetComp:
    raise NotImplementedError()


def generate_Slice() -> ast.Slice:
    raise NotImplementedError()


def generate_Starred() -> ast.Starred:
    raise NotImplementedError()


def generate_Subscript() -> ast.Subscript:
    raise NotImplementedError()


def generate_Tuple() -> ast.Tuple:
    raise NotImplementedError()


def generate_UnaryOp() -> ast.UnaryOp:
    raise NotImplementedError()


def generate_Yield() -> ast.Yield:
    raise NotImplementedError()


def generate_YieldFrom() -> ast.YieldFrom:
    raise NotImplementedError()


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
    raise NotImplementedError()


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
    raise NotImplementedError()


def generate_FunctionType() -> ast.FunctionType:
    raise NotImplementedError()


def generate_Interactive() -> ast.Interactive:
    raise NotImplementedError()


def generate_Module() -> ast.Module:
    raise NotImplementedError()


# def generate_slice() -> ast.slice:
#     x = random.choice([])
#     return x()


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
    raise NotImplementedError()


def generate_MatchClass() -> ast.MatchClass:
    raise NotImplementedError()


def generate_MatchMapping() -> ast.MatchMapping:
    raise NotImplementedError()


def generate_MatchOr() -> ast.MatchOr:
    raise NotImplementedError()


def generate_MatchSequence() -> ast.MatchSequence:
    raise NotImplementedError()


def generate_MatchSingleton() -> ast.MatchSingleton:
    raise NotImplementedError()


def generate_MatchStar() -> ast.MatchStar:
    raise NotImplementedError()


def generate_MatchValue() -> ast.MatchValue:
    raise NotImplementedError()


def generate_type_param() -> ast.type_param:
    x = random.choice([generate_ParamSpec, generate_TypeVar, generate_TypeVarTuple])
    return x()


def generate_ParamSpec() -> ast.ParamSpec:
    raise NotImplementedError()


def generate_TypeVar() -> ast.TypeVar:
    raise NotImplementedError()


def generate_TypeVarTuple() -> ast.TypeVarTuple:
    raise NotImplementedError()


def generate_type_ignore() -> ast.type_ignore:
    x = random.choice([generate_TypeIgnore])
    return x()


def generate_TypeIgnore() -> ast.TypeIgnore:
    raise NotImplementedError()
