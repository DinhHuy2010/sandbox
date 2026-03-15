from __future__ import annotations

import builtins
from functools import wraps
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyinterpeter import PythonInterpeter


def patch_builtins(ns: dict[str, Any], interpeter: PythonInterpeter) -> dict[str, Any]:
    @wraps(builtins.globals)
    def globals():
        return interpeter.frame.globalvars

    @wraps(builtins.locals)
    def locals():
        return interpeter.frame.localvars

    ns.update({"globals": globals, "locals": locals})
    return ns
