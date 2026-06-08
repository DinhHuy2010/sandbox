"""Utility functions for handling virtual environment metadata."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

SCRIPT_GATHER_DATA = """
import json, platform, sys, sysconfig
print(json.dumps({
    "version": platform.python_version(),
    "executable": sys.executable,
    "prefix": sys.prefix,
    "base_prefix": sys.base_prefix,
    "exec_prefix": sys.exec_prefix,
    "base_exec_prefix": sys.base_exec_prefix,
    "paths": sysconfig.get_paths(),
}))
"""


def parse_venv_info(path: Path) -> dict[str, str] | None:
    """Parse virtual environment metadata.

    Parameters
    ----------
    path: pathlib.Path
        Path to a virtual environment directory containing ``pyvenv.cfg``.

    Returns
    -------
    dict[str, str] | None
        Parsed metadata from the virtual environment configuration.

    Raises
    ------
    KeyError
        If required version metadata is missing from ``pyvenv.cfg``.
    """
    data = {}
    cfg = path / "pyvenv.cfg"
    try:
        f = cfg.open(encoding="utf-8")
    except FileNotFoundError:
        return None
    with f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            data[key.strip()] = value.strip()
    return data


def gather_from_python(path: Path) -> dict[str, Any]:
    """Gather environment metadata by executing the Python interpreter.

    Parameters
    ----------
    path: pathlib.Path
        Path to the Python executable

    Returns
    -------
    dict[str, Any]
        Gathered metadata from the Python interpreter.
    """
    result = subprocess.run(
        [str(path), "-c", SCRIPT_GATHER_DATA],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return json.loads(result.stdout)
