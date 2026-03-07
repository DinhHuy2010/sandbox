from importlib.machinery import ModuleSpec
import pkgutil
import site
import sysconfig

import dis
from pathlib import Path


def module_globals_no_imports(spec: ModuleSpec) -> set[str]:
    if not spec or not spec.origin or not spec.origin.endswith(".py"):
        return set()

    src = Path(spec.origin).read_text()
    code = compile(src, spec.origin, "exec")

    names = set()
    skip = set()

    instructions = list(dis.get_instructions(code))

    for i, instr in enumerate(instructions):
        if instr.opname == "IMPORT_NAME":
            # next STORE_NAME belongs to import
            if i + 1 < len(instructions):
                nxt = instructions[i + 1]
                if nxt.opname in {"STORE_NAME", "STORE_GLOBAL"}:
                    skip.add(nxt.argval)

        elif instr.opname in {"STORE_NAME", "STORE_GLOBAL"}:
            if instr.argval not in skip:
                names.add(instr.argval)

    return names


paths = [
    *site.getsitepackages(),
    sysconfig.get_path("stdlib"),
    sysconfig.get_path("platstdlib"),
]
for p in pkgutil.walk_packages(paths):
    spec = p.module_finder.find_spec(p.name)
    print(p.name)
    if spec is None:
        continue
    for name in module_globals_no_imports(spec):
        print(f"{p.name}.{name}")
