import ast
from importlib.util import module_from_spec
import site
import sysconfig
from importlib.machinery import ModuleSpec
from pathlib import Path
from pkgutil import walk_packages

from typing import Generator


def modules_globals_via_import(spec: ModuleSpec) -> Generator[str, None, None]:
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    yield from dir(module)


def module_globals(spec: ModuleSpec) -> Generator[str, None, None]:
    if not spec.origin or not spec.origin.endswith(".py"):
        return modules_globals_via_import(spec)

    src = Path(spec.origin).read_text(encoding="utf-8")
    code = ast.parse(src, filename=spec.origin)
    for node in code.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            yield node.name
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    yield target.id


paths = [
    *site.getsitepackages(),
    sysconfig.get_path("stdlib"),
    sysconfig.get_path("platstdlib"),
]

for p in walk_packages(paths):
    spec = p.module_finder.find_spec(p.name)
    if not spec:
        continue
    for name in module_globals(spec):
        print(f"{p.name}.{name}")
