"""Facilities for discovering Python environments on the system."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

from dhinstaller.environments import Environment
from dhinstaller.environments.utils import gather_from_python

PYTHON_REGEX_EXE = re.compile(r"python(?:\d+(?:\.\d+)?[-a-z]*)?")


def environment_from_interpreter(interpreter: Path) -> Environment:
    """Create an Environment object from a given Python interpreter path.

    Parameters
    ----------
    interpreter: pathlib.Path
        Path to a Python interpreter executable.

    Returns
    -------
    Environment
        An Environment object populated from the specified interpreter.

    Raises
    ------
    FileNotFoundError
        If the specified interpreter path does not exist.
    """
    if not interpreter.exists():
        raise FileNotFoundError(f"Python interpreter not found at: {interpreter}")

    data = gather_from_python(interpreter)
    return Environment(
        executable=interpreter,
        version=data["version"],
        scheme_paths=data["paths"],
    )


# Discovering all Python(s) via PATH

is_wsl = "WSL_DISTRO_NAME" in os.environ
PATH_SEP = os.pathsep
# shutil
# CMD defaults in Windows 10
_WIN_DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC"

WINDOWS_PATHEXT = tuple(
    x.lower() for x in os.environ.get("PATHEXT", _WIN_DEFAULT_PATHEXT).split(";")
)


def _which_map(
    *, extra_paths: list[str] | None = None, exclude_windows_on_wsl: bool = True
):
    def is_callable_from_cmd(path: os.DirEntry) -> bool:
        if os.name == "nt":
            return path.is_file() and path.name.lower().endswith(WINDOWS_PATHEXT)
        else:
            return path.is_file() and os.access(path, os.X_OK)

    paths = os.environ["PATH"].split(PATH_SEP)
    if extra_paths:
        paths.extend(extra_paths)
    if is_wsl and exclude_windows_on_wsl:
        paths = [p for p in paths if not p.startswith("/mnt/c/")]
    for p in paths:
        try:
            it = os.scandir(p)
        except FileNotFoundError:
            continue
        except PermissionError:
            continue
        else:
            with it:
                for f in it:
                    full_path = os.path.join(p, f.name)  # noqa: PTH118
                    if is_callable_from_cmd(f):
                        yield f.name, full_path


def discover_environments() -> Iterable[Environment]:
    """Discover Python environments available on the system.

    This function searches for Python interpreters in the system PATH and
    attempts to create Environment objects from them.

    Returns
    -------
    Iterable[Environment]
        An iterable of Environment objects representing discovered Python environments.
    """
    for name, path in _which_map():
        if PYTHON_REGEX_EXE.fullmatch(name):
            try:
                yield environment_from_interpreter(Path(path))
            except Exception:
                continue
