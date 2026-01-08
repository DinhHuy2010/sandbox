import pydoc
import sys
from typing import Any

from can_ada import URLSearchParams


def _fetch_python_version(
    path_args: tuple[str, ...], query_params: URLSearchParams, fragment: str
) -> Any:
    output = query_params.get("output") or "default"
    version_info = sys.version_info
    if output == "default":
        return version_info
    elif output == "string":
        return f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    elif output == "major":
        return version_info.major
    elif output == "minor":
        return version_info.minor
    elif output == "micro":
        return version_info.micro
    elif output == "json":
        return {
            "full": f"{version_info.major}.{version_info.minor}.{version_info.micro}",
            "major": version_info.major,
            "minor": version_info.minor,
            "micro": version_info.micro,
            "releaselevel": version_info.releaselevel,
            "serial": version_info.serial,
        }

    else:
        raise ValueError(f"Unknown output type: {output}")


def _resolve_python_import(
    path_args: tuple[str, ...], query_params: URLSearchParams, fragment: str
) -> Any:
    module_path = path_args[0]
    obj = pydoc.locate(module_path)
    output = query_params.get("type") or "default"
    if output == "default":
        return obj
    elif output == "json":
        return {"module_path": module_path, "obj": obj, "type": type(obj)}
    return obj


def __protocol_metadata__() -> Any:
    return {
        "scheme": "python",
        "endpoints": {
            "version": _fetch_python_version,
            "import": _resolve_python_import,
        },
    }
