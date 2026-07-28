from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import SimpleNamespace


def require(
    module_list: str | list[str] | dict[str, str], /, *modules: str | dict[str, str]
) -> SimpleNamespace:
    from importlib import import_module
    from inspect import currentframe, getouterframes
    from types import SimpleNamespace

    module_names: dict[str, str] = {}

    if isinstance(module_list, str):
        module_names[module_list] = module_list
    elif isinstance(module_list, list):
        for module in module_list:
            module_names[module] = module
    for module in modules:
        if isinstance(module, str):
            module_names[module] = module
        else:
            module_names.update(module)
    caller_frame_info = getouterframes(currentframe())[1]
    frame = caller_frame_info.frame
    loaded_modules: dict[str, object] = {}

    for module, alias in module_names.items():
        imported_module = import_module(module)
        loaded_modules[alias] = imported_module
    if frame.f_code.co_name == "<module>":
        frame.f_globals.update(loaded_modules)
    return SimpleNamespace(**loaded_modules)


require(
    "math",
    "sys",
    "json",
    "os",
    "re",
    "datetime",
    "random",
    "collections",
    "itertools",
    "functools",
    "operator",
    "subprocess",
    "threading",
    "asyncio",
    "socket",
    "struct",
    "pickle",
    "copy",
)
