from __future__ import annotations

import ast
from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from pyinterpeter import PythonInterpeter


def generate_signature(
    interpreter: PythonInterpeter, node: ast.FunctionDef
) -> Signature:

    def resolve_expr(node_or_none: ast.expr | None):
        if node_or_none is None:
            return Parameter.empty
        return interpreter.visit(node_or_none)

    params: list[Parameter] = []
    args = node.args

    # return annotation
    return_anno = resolve_expr(node.returns)

    # ---- positional parameters ----

    posargs = args.posonlyargs + args.args
    defaults = args.defaults
    defaults_offset = len(posargs) - len(defaults)

    for i, arg in enumerate(posargs):
        annotation = resolve_expr(arg.annotation)

        if i >= defaults_offset:
            default = resolve_expr(defaults[i - defaults_offset])
        else:
            default = Parameter.empty

        kind = (
            Parameter.POSITIONAL_ONLY
            if arg in args.posonlyargs
            else Parameter.POSITIONAL_OR_KEYWORD
        )

        params.append(
            Parameter(
                arg.arg,
                kind,
                default=default,
                annotation=annotation,
            )
        )

    # ---- *args ----

    if args.vararg is not None:
        params.append(
            Parameter(
                args.vararg.arg,
                Parameter.VAR_POSITIONAL,
                annotation=resolve_expr(args.vararg.annotation),
            )
        )

    # ---- keyword-only ----

    for kwarg, default_node in zip(args.kwonlyargs, args.kw_defaults):
        annotation = resolve_expr(kwarg.annotation)
        default = resolve_expr(default_node)
        params.append(
            Parameter(
                kwarg.arg,
                Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
        )

    # ---- **kwargs ----

    if args.kwarg is not None:
        params.append(
            Parameter(
                args.kwarg.arg,
                Parameter.VAR_KEYWORD,
                annotation=resolve_expr(args.kwarg.annotation),
            )
        )

    return Signature(params, return_annotation=return_anno)


def _build_raw(f: Function) -> Callable[..., Any]:
    from pyinterpeter import ReturnSignal

    def func(*args, **kwargs):
        with f.interpeter.push_frame(f.node):
            f.interpeter.frame.prev = f.__closure_frame__
            bindings = f.__signature__.bind(*args, **kwargs)
            bindings.apply_defaults()
            f.interpeter.frame.localvars.update(bindings.arguments)
            for stmt in f.node.body:
                try:
                    f.interpeter.visit(stmt)
                except ReturnSignal as rs:
                    return rs.value
        return None

    for decorator in reversed(f.node.decorator_list):
        decorator_func = f.interpeter.visit(decorator)
        func = decorator_func(func)

    return func


@dataclass
class Function:
    node: ast.FunctionDef
    interpeter: PythonInterpeter

    def __post_init__(self):
        self.__signature__ = generate_signature(self.interpeter, self.node)
        self.__doc__ = ast.get_docstring(self.node)
        self.__name__ = self.node.name
        self.__module__ = self.interpeter.frame.globalvars.get("__name__", "__main__")  # type: ignore
        self.__annotations__ = {
            param.name: param.annotation
            for param in self.__signature__.parameters.values()
            if param.annotation is not Parameter.empty
        }
        if self.__signature__.return_annotation is not Parameter.empty:
            self.__annotations__["return"] = self.__signature__.return_annotation
        self.__closure_frame__ = self.interpeter.frame
        self.__real_func__ = None

    def __call__(self, *args, **kwargs):
        if self.__real_func__ is None:
            self.__real_func__ = _build_raw(self)
        return self.__real_func__(*args, **kwargs)
