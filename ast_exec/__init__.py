# type: ignore # ruff: noqa
# fmt: off
__ast = __import__("ast")
__fix_ast = lambda node: __ast.fix_missing_locations(node)
__build_astmod = lambda body: __fix_ast(__ast.Module(body=body, type_ignores=[]))
pyast_exec = lambda module, ns=None: (locals().__setitem__("__ns", ns or {}), exec(compile(module, filename="<ast_exec>", mode="exec"), {}, locals()["__ns"]), locals()["__ns"])[-1]
mutate = lambda obj, ns: (tuple(setattr(obj, k, v) for k, v in ns.items()), obj)[-1]
raise_exception = lambda exc, cause=None: pyast_exec(
    __build_astmod([__ast.Raise(
        exc=__ast.Name(id="exc", ctx=__ast.Load()),
        cause=__ast.Name(id="cause", ctx=__ast.Load()) if cause is not None else None,
    )]),
    {"exc": exc, "cause": cause},
)
