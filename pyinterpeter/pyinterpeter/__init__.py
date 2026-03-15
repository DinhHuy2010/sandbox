# pyright: standard

from __future__ import annotations

import ast
import reprlib
from contextlib import contextmanager
from dataclasses import dataclass
from sys import stderr
from types import SimpleNamespace
from typing import Any, Generator
from warnings import warn

from pyinterpeter.builtins_patch import patch_builtins
from pyinterpeter.constants import OPERATORS
from pyinterpeter.frame import Frame
from pyinterpeter.functions import Function
from pyinterpeter.future import Future
from pyinterpeter.future import resolve_future as _resolve_future
from pyinterpeter.options import Options


class NoBinOp(RuntimeError):
    pass


def execute_binop(
    op: ast.operator, left: Any, right: Any, future_enabled: bool
) -> Any | Future[Any]:
    def doit():
        out = OPERATORS.get(type(op))
        if out is None:
            raise NoBinOp
        fn, _ = out
        return fn(left, right)

    if future_enabled:
        return Future(fn=doit, args=(), kwargs={})
    return doit()


class PythonInterpeter(ast.NodeVisitor):
    def __init__(
        self,
        globals: dict[str, Any] | None = None,
        builtins: dict[str, Any] | None = None,
        *,
        options: Options | None = None,
    ) -> None:
        globals = globals or {}
        self.frame = Frame.new(
            globalvars=globals,
            builtins=patch_builtins(builtins or {}, self),
        )
        self.options = options or Options()
        self.reserved_data = {
            "__piflags__": SimpleNamespace(options=self.options),
            "__pihelper__": SimpleNamespace(
                resolve_future=_resolve_future, Future=Future
            ),
        }
        self.frame.globalvars.update(self.reserved_data)

    def debug(self, comp: str, msg: str) -> None:
        if self.options.debug:
            print(f"[{comp}]: {msg}", file=stderr)

    def resolve(self, frame: Frame, name: str) -> Any:
        cf = frame
        f = frame
        self.debug("name_resolver", f"Finding {name!r} on frame {f.format_id()}")
        while cf is not None:
            self.debug(
                "name_resolver", f"Finding {name!r} on locals on frame {cf.format_id()}"
            )
            if name in cf.localvars:
                self.debug(
                    "name_resolver",
                    f"Found {name!r} on locals on frame {cf.format_id()}",
                )
                return cf.localvars[name]
            cf = cf.prev

        if name in f.globalvars:
            self.debug(
                "name_resolver", f"Found {name!r} on globals on frame {f.format_id()}"
            )
            return f.globalvars[name]
        elif name in f.builtins:
            self.debug(
                "name_resolver", f"Found {name!r} on builtins on frame {f.format_id()}"
            )
            return f.builtins[name]

        self.debug("name_resolver", "Failed to find, erroring")
        raise NameError(f"Not found: {name!r}", name=name)

    @contextmanager
    def push_frame(self, node: ast.AST) -> Generator[None, None, None]:
        prev = self.frame
        next_frame = self.frame.next(node)
        self.debug(
            "frame",
            f"Pushing frame {next_frame.format_id()} (prev: {prev.format_id()})",
        )
        try:
            self.frame = next_frame
            yield
        finally:
            self.debug(
                "frame",
                f"Popping frame {self.frame.format_id()} (prev: {prev.format_id()})",
            )
            self.frame = prev

    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self.visit(stmt)

    def visit_Expr(self, node: ast.Expr):
        return self.visit(node.value)

    def visit_Call(self, node: ast.Call):
        func = self.visit(node.func)

        args = []
        kwargs = {}

        for arg in node.args:
            if isinstance(arg, ast.Starred):
                args.extend(self.visit(arg.value))
            else:
                args.append(self.visit(arg))

        for kw in node.keywords:
            if kw.arg is None:
                kwargs.update(self.visit(kw.value))
            else:
                kwargs[kw.arg] = self.visit(kw.value)

        return func(*args, **kwargs)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            return self.resolve(self.frame, node.id)
        elif isinstance(node.ctx, ast.Store):
            if node.id in self.reserved_data:
                raise RuntimeError(f"can't set reserved name {node.id!r}")
            return node.id
        raise RuntimeError

    def visit_Constant(self, node: ast.Constant):
        return node.value

    def visit_Assign(self, node):
        def define(name_node: ast.Name, value: Any):
            name = self.visit_Name(name_node)
            self.debug("assign", f"Assigning {name!r} to {value!r}")
            self.frame.localvars[name] = value

        value = self.visit(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                define(target, value)
            else:
                warn(f"Warning: unknown target: {type(target)!r}")

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        try:
            return execute_binop(node.op, left, right, self.options.future_op_enabled)
        except NoBinOp:
            warn(f"Warning: no binary operator found for {type(node.op)!r}")
            return None

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Load):
            return getattr(self.visit(node.value), node.attr)
        raise RuntimeError

    def visit_If(self, node):
        if self.visit(node.test):
            for stmt in node.body:
                self.visit(stmt)
        else:
            for stmt in node.orelse:
                self.visit(stmt)

    def visit_Assert(self, node):
        if not self.visit(node.test):
            raise AssertionError

    def visit_Compare(self, node):
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if type(op) not in OPERATORS:
                warn(f"Warning: no compare operator found for {type(op)!r}")
                return False
            fn, _ = OPERATORS[type(op)]
            if not fn(left, right):
                return False
            left = right
        return True

    def visit_FunctionDef(self, node):
        func = Function(node, self)
        self.frame.localvars[node.name] = func
        return func

    def visit_Return(self, node):
        if node.value is None:
            raise ReturnSignal(None)
        raise ReturnSignal(self.visit(node.value))

    def visit_BoolOp(self, node: ast.BoolOp):
        values = node.values

        if isinstance(node.op, ast.And):
            result = self.visit(values[0])
            for v in values[1:]:
                if not result:
                    return result
                result = self.visit(v)
            return result

        elif isinstance(node.op, ast.Or):
            result = self.visit(values[0])
            for v in values[1:]:
                if result:
                    return result
                result = self.visit(v)
            return result

        else:
            raise RuntimeError(f"Unknown BoolOp {type(node.op)!r}")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)

        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.Invert):
            return ~operand

        raise RuntimeError(f"Unknown unary op {type(node.op)!r}")

    def visit_Subscript(self, node: ast.Subscript):
        obj = self.visit(node.value)
        index = self.visit(node.slice)
        return obj[index]

    def visit_While(self, node: ast.While):
        while self.visit(node.test):
            for stmt in node.body:
                self.visit(stmt)

    def visit_For(self, node: ast.For):
        iterable = self.visit(node.iter)

        for value in iterable:
            if not isinstance(node.target, ast.Name):
                warn(f"Warning: unknown For target: {type(node.target)!r}")
                continue
            name = node.target.id
            self.frame.localvars[name] = value

            for stmt in node.body:
                self.visit(stmt)

    def visit_AugAssign(self, node):
        if not isinstance(node.target, ast.Name):
            warn(f"Warning: unknown AugAssign target: {type(node.target)!r}")
            return None
        name = node.target.id
        target = self.visit(node.target)
        value = self.visit(node.value)
        try:
            result = execute_binop(
                node.op, target, value, self.options.future_op_enabled
            )
            self.frame.localvars[name] = result
            return result
        except NoBinOp:
            warn(f"Warning: no binary operator found for {type(node.op)!r}")
            return None

    def visit_Lambda(self, node):
        def lambda_node_to_function(node: ast.Lambda) -> Function:
            func_def = ast.FunctionDef(
                name="<lambda>",
                args=node.args,
                body=[ast.Return(value=node.body)],
                decorator_list=[],
                type_comment=None,
                type_params=[],
            )
            return Function(func_def, self)

        return lambda_node_to_function(node)

    def visit_List(self, node):
        return [self.visit(e) for e in node.elts]

    def visit_Tuple(self, node):
        return tuple(self.visit(e) for e in node.elts)

    def visit_Set(self, node):
        return {self.visit(e) for e in node.elts}

    def visit_Dict(self, node):
        return {
            self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values) if k
        }

    def visit(self, node) -> Any:
        def print_node_unparsed(node: ast.AST) -> None:
            lines = ast.unparse(node).splitlines()
            start_lineno = getattr(node, "lineno", 1)
            for i, line in enumerate(lines, start=start_lineno):
                self.debug("interpeter", f"{i}: {line}")

        t = type(node).__name__
        caller = getattr(self, f"visit_{t}", None)
        if caller is None:
            self.debug(
                "interpeter", f"no visit found for {t!r}, falling back to generic_visit"
            )
            print_node_unparsed(node)
            return self.generic_visit(node)
        if not isinstance(node, ast.Module):
            self.debug(
                "interpeter",
                f"-> {t!r} at line {getattr(node, 'lineno', '?')} in frame {self.frame.format_id()}",
            )
            print_node_unparsed(node)
        out = caller(node)
        if not isinstance(node, ast.Module):
            self.debug("interpeter", f"<- {t!r} returns {reprlib.repr(out)}")
        return out

    def state(self) -> InterpeterState:
        return InterpeterState(self.frame, self.options)


class Signal(Exception):
    pass


@dataclass
class ReturnSignal(Signal):
    value: Any

    def __str__(self) -> str:
        return f"<return signal {self.value!r}>"


@dataclass
class BreakSignal(Signal):
    def __str__(self) -> str:
        return "<break signal>"


@dataclass
class ContinueSignal(Signal):
    def __str__(self) -> str:
        return "<continue signal>"


@dataclass
class InterpeterState:
    frame: Frame
    options: Options


@dataclass
class ScriptRunner:
    options: Options | None = None

    def run(
        self,
        code: str,
        globals: dict[str, Any] | None = None,
        builtins: dict[str, Any] | None = None,
        filename: str | None = None,
    ) -> InterpeterState:
        interpeter = PythonInterpeter(globals, builtins, options=self.options)
        interpeter.debug("runner", f"Running code from {filename or '<stdin>'}")
        interpeter.debug("runner", "Options:")
        interpeter.debug("runner", f"  debug: {interpeter.options.debug}")
        interpeter.debug(
            "runner", f"  future_op_enabled: {interpeter.options.future_op_enabled}"
        )
        tree = ast.parse(code, filename=filename or "<stdin>")
        interpeter.visit(tree)
        return interpeter.state()
