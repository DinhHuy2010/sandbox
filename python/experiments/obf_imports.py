import ast
import inspect
import random
from dataclasses import dataclass
from importlib import import_module
from types import ModuleType


@dataclass
class ModuleInfo:
    name: str
    members: list[str]

    def __post_init__(self):
        self.members.sort()


def import_from_module(module: ModuleType) -> ModuleInfo:
    def get_member_names(module: ModuleType) -> list[str]:
        try:
            ls = getattr(module, "__all__", None)
            if ls is not None:
                return ls
        except Exception:
            pass
        return [
            name for name, _ in inspect.getmembers(module) if not name.startswith("_")
        ]

    return ModuleInfo(name=module.__name__, members=get_member_names(module))


_rand = random.SystemRandom()


def generate_table(module_info: ModuleInfo) -> dict[str, str]:
    table: dict[str, str] = {}
    for member in module_info.members:
        generated_id = ""
        generated_id += _rand.choice("abcdefghijklmnopqrstuvwxyz")
        generated_id += "".join(
            _rand.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=31)
        )
        table[generated_id] = member
    return table


def generate_module_ast(module_info: ModuleInfo) -> ast.Module:
    body: list[ast.stmt] = []
    add_stmt = body.append
    modref = f"module_{_rand.randint(0, 9999)}"
    add_stmt(
        ast.Assign(
            targets=[ast.Name(id=modref, ctx=ast.Store())],
            value=ast.Call(
                func=ast.Name(id="__import__", ctx=ast.Load()),
                args=[ast.Constant(value=module_info.name)],
                keywords=[],
            ),
        )
    )
    table = generate_table(module_info)
    for obf_name, real_name in table.items():
        add_stmt(
            ast.Assign(
                targets=[ast.Name(id=obf_name, ctx=ast.Store())],
                value=ast.Attribute(
                    value=ast.Name(id=modref, ctx=ast.Load()),
                    attr=real_name,
                    ctx=ast.Load(),
                ),
            )
        )

    return ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))


p = import_from_module(import_module("math"))
ast_module = generate_module_ast(p)
print(ast.unparse(ast_module))
