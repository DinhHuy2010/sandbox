# from attrs import define


# @define
# class Goto(Exception):
#     label: str

#     def __str__(self):
#         return f"goto {self.label}"

# def a():
#     print("a")
#     raise Goto("b")

# if __name__ == "__main__":
#     try:
#         a()
#     except Goto as e:
#         match e.label:
#             case "b":
#                 print("b")


from importlib.metadata import Distribution
import json
import os
from pathlib import Path
import subprocess
from typing import Iterable

from attr import define
from attrs import field
from packaging.version import Version

is_wsl = "WSL_DISTRO_NAME" in os.environ
PATH_SEP = ";" if os.name == "nt" else ":"
# shutil
# CMD defaults in Windows 10
_WIN_DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD;.VBS;.JS;.WS;.MSC"

WINDOWS_PATHEXT = tuple(
    x.lower() for x in os.environ.get("PATHEXT", _WIN_DEFAULT_PATHEXT).split(";")
)


def which_map(
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
                    # full_path = os.path.join(p, f.name)
                    if is_callable_from_cmd(f):
                        yield f.name, os.path.join(p, f.name)


@define
class PythonEnvironment:
    version: Version
    executable: str
    prefix: str
    base_prefix: str
    exec_prefix: str
    base_exec_prefix: str
    scheme_paths: dict[str, str]

    _venv_info: dict | None = field(default=None, init=False, repr=False)

    @property
    def version_tuple(self):
        return (self.version.major, self.version.minor, self.version.micro)

    @property
    def is_venv(self):
        return self.prefix != self.base_prefix

    @property
    def venv_info(self):
        if self._venv_info is not None:
            return self._venv_info

        p = Path(self.scheme_paths["data"])
        # cand_venv_path = p.parent.parent.parent
        pyvenv_cfg = p / "pyvenv.cfg"
        if not pyvenv_cfg.exists():
            # return cand_venv_path
            return None
        data = {}
        with pyvenv_cfg.open() as f:
            raw = f.read()
            for line in raw.splitlines():
                if line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                data[key] = value
        self._venv_info = data
        return data

    @property
    def venv_name(self):
        info = self.venv_info
        if info is None:
            return None
        return info.get("prompt")

    def packages(self) -> Iterable[Distribution]:
        # site_packages = self.scheme_paths.get("purelib")
        # if site_packages is None:
        #     return iter(())

        def gen(package_dir: str):
            with os.scandir(package_dir) as it:
                for entry in it:
                    if entry.is_dir() and entry.name.endswith(
                        (".dist-info", ".egg-info")
                    ):
                        yield Distribution.at(entry.path)

        # return gen(site_packages)
        for scheme in ("purelib", "platlib"):
            package_dir = self.scheme_paths.get(scheme)
            if package_dir is not None:
                yield from gen(package_dir)


SCRIPT = """
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


def get_python(executable: str) -> PythonEnvironment | None:
    proc = subprocess.run(
        [executable, "-c", SCRIPT],
        # check=True,
        text=True,
        timeout=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
    # proc.check_returncode()
    if proc.returncode != 0:
        return None
    if proc.stdout is None:
        return None
    out = proc.stdout.strip()
    try:
        data = json.loads(out)
        return PythonEnvironment(
            version=Version(data["version"].strip("+")),
            executable=data["executable"],
            prefix=data["prefix"],
            base_prefix=data["base_prefix"],
            exec_prefix=data["exec_prefix"],
            base_exec_prefix=data["base_exec_prefix"],
            scheme_paths=data["paths"],
        )
    except json.JSONDecodeError:
        return None


# pprint(list(which_map()))
for name, path in which_map():
    if not name.startswith("python"):
        continue
    # print(f"{name}: {path} {get_python(path)}")
    # print(f"{name}: {path}")
    environment = get_python(path)
    if environment is None:
        # print(f"{name}: {path} (failed to get environment)")
        continue
    print(f"Python {environment.version} ({environment.executable})")
    scripts = environment.scheme_paths.get("scripts")
    if scripts is None:
        continue
    scripts_path = Path(scripts)
    # print(enviroment.packages())
    for pkg in environment.packages():
        print(f"  {pkg.name}=={pkg.version}")
