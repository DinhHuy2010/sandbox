from importlib.util import find_spec
from pathlib import Path
from pkgutil import walk_packages
import sysconfig
import site


def find_source_file_for_module(module_name: str):
    spec = find_spec(module_name)
    if spec is None:
        raise ImportError(f"Module '{module_name}' not found")
    if spec.origin is None:
        raise ImportError(f"Module '{module_name}' does not have an origin")
    try:
        o = Path(spec.origin).resolve(strict=True)
    except FileNotFoundError:
        raise ImportError(f"Module '{module_name}' does not have a source file")
    if o.is_file():
        return o
    else:
        raise ImportError(f"Module '{module_name}' does not have a source file")


stdlib = sysconfig.get_paths()["stdlib"]
platstdlib = sysconfig.get_paths()["platstdlib"]
site_packages = site.getsitepackages()

d = set([stdlib, platstdlib] + site_packages)
for info in walk_packages(d, onerror=lambda x: None):
    try:
        source_file = find_source_file_for_module(info.name)
    except ImportError:
        source_file = None
    print(info.name, source_file)
