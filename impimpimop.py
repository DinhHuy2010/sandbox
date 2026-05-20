from dataclasses import dataclass
from datetime import datetime
import importlib
from importlib.abc import Loader
import importlib.machinery
from importlib.metadata import PathDistribution
from importlib.util import spec_from_loader
from pathlib import PurePosixPath
import sys
from types import ModuleType
from typing import Generator
from zipfile import Path as ZFPath
from zipfile import ZipFile

from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
from packaging.version import Version
from pypi_simple import DistributionPackage, PyPISimple

from rangerespv2 import HTTPFile

SYS_TAGS_ORDERED = tuple(sys_tags())
SYS_TAG_RANK = {tag: i for i, tag in enumerate(SYS_TAGS_ORDERED)}


def best_tag_rank(pkg: DistributionPackage) -> int | None:
    try:
        _, _, _, wheel_tags = parse_wheel_filename(pkg.filename)
    except Exception:
        return None
    best: int | None = None
    for tag in wheel_tags:
        rank = SYS_TAG_RANK.get(tag)
        if rank is not None and (best is None or rank < best):
            best = rank
    return best


def is_suitable_package(pkg: DistributionPackage) -> bool:
    if pkg.package_type != "wheel":
        return False
    requirement = Requirement(pkg.project)  # type: ignore
    if not requirement.specifier.contains(pkg.version, prereleases=False):
        return False
    return best_tag_rank(pkg) is not None


def choose_best_package(
    packages: list[DistributionPackage],
) -> DistributionPackage | None:
    if not packages:
        return None

    def build_candidates() -> Generator[
        tuple[DistributionPackage, Version, int | None, datetime | None], None, None
    ]:
        for p in packages:
            if p.project is None:
                continue
            if p.version is None:
                continue
            if is_suitable_package(p):
                yield ((p, Version(p.version), best_tag_rank(p), p.upload_time))

    out = max(build_candidates(), key=lambda p: p[1:], default=None)
    if out is None:
        return None
    return out[0]


class RemoteWheelOverHTTP:
    def __init__(self, url: str):
        self.url = url
        self._wheel: HTTPFile | None = None

    def _get_wheel(self) -> HTTPFile:
        if self._wheel is None:
            self._wheel = HTTPFile(self.url)
        return self._wheel

    def close(self):
        if self._wheel is not None:
            self._wheel.close()
            self._wheel = None

    def zipfile(self) -> ZipFile:
        return ZipFile(self._get_wheel())

    def dist_info_path(self) -> ZFPath:
        zf = ZFPath(self.zipfile())
        return next(zf.glob("*.dist-info"))

    def meta_dist(self) -> PathDistribution:
        dist_info = self.dist_info_path()
        return PathDistribution(dist_info)


@dataclass(frozen=True)
class ResolvedImport:
    fullname: str
    wheel_path: str
    kind: str  # "module", "package", "extension"
    is_package: bool


class PyPIRemoteLoader(Loader):
    def __init__(self, remote):
        self.remote = remote

    def _zip_root(self) -> ZFPath:
        return ZFPath(self.remote.zipfile())

    def _candidate_paths(self, fullname: str) -> list[tuple[str, str, bool]]:
        """
        Return candidates in import resolution order.

        Each item is:
            (wheel-relative-path, kind, is_package)
        """
        parts = fullname.split(".")
        base = PurePosixPath(*parts)

        candidates: list[tuple[str, str, bool]] = []

        # 1. package first or module first?
        # Python's import machinery conceptually resolves by finder/spec logic,
        # but for a wheel-backed manual resolver you usually want to check:
        #   package (__init__) and module (.py)
        # in a deterministic order.
        #
        # Checking package first can be useful when both are present,
        # though that situation is unusual / invalid-ish.
        candidates.append((str(base / "__init__.py"), "package", True))
        candidates.append((str(base) + ".py", "module", False))

        # Compiled/native extension modules
        for suffix in importlib.machinery.EXTENSION_SUFFIXES:
            candidates.append((str(base) + suffix, "extension", False))

        return candidates

    def resolve_fullname(self, fullname: str) -> ResolvedImport | None:
        zf = self._zip_root()

        for relpath, kind, is_package in self._candidate_paths(fullname):
            candidate = zf / relpath
            if candidate.exists():
                return ResolvedImport(
                    fullname=fullname,
                    wheel_path=relpath,
                    kind=kind,
                    is_package=is_package,
                )

        return None

    def exec_module(self, module: ModuleType) -> None:
        resolved = self.resolve_fullname(module.__name__)
        if resolved is None:
            raise ImportError(f"Cannot resolve {module.__name__!r} in remote wheel")

        if resolved.kind in {"module", "package"}:
            zf = self._zip_root()
            src_path = zf / resolved.wheel_path
            source = src_path.read_text(encoding="utf-8")
            code = compile(source, resolved.wheel_path, "exec")

            module.__file__ = resolved.wheel_path
            module.__loader__ = self
            if resolved.is_package:
                module.__package__ = module.__name__
                module.__path__ = [str(PurePosixPath(resolved.wheel_path).parent)]
            else:
                module.__package__ = module.__name__.rpartition(".")[0]

            exec(code, module.__dict__)
            return

        if resolved.kind == "extension":
            raise ImportError(
                f"{module.__name__!r} resolves to native extension "
                f"{resolved.wheel_path!r}; extract to disk and use ExtensionFileLoader"
            )

        raise ImportError(f"Unsupported resolved kind: {resolved.kind}")


class PyPIRemoteFinder(importlib.abc.MetaPathFinder):
    def __init__(self, client: PyPISimple, package_to_imports: dict[str, str]):
        self.client = client
        self.package_to_imports = package_to_imports

    def _find_project_by_import_name(self, fullname: str) -> DistributionPackage | None:
        # This is a heuristic; it won't always work.
        # For example, "google.cloud.storage" is a valid import path for the
        # "google-cloud-storage" package.
        top_level = fullname.split(".")[0]
        if top_level in {*sys.builtin_module_names, *sys.stdlib_module_names}:
            return None
        project_name = self.package_to_imports.get(top_level, top_level)
        project_page = self.client.get_project_page(project_name)
        return choose_best_package(project_page.packages)

    def find_spec(self, fullname: str, path, target=None):
        dist = self._find_project_by_import_name(fullname)
        print("Finding spec for", fullname, "->", dist)
        if dist is None:
            return None

        wheel = RemoteWheelOverHTTP(dist.url)
        loader = PyPIRemoteLoader(wheel)

        # We can defer resolution of the actual file within the wheel until
        # loader.exec_module, so we don't need to check for existence here.

        return spec_from_loader(fullname, loader, origin=dist.url)


client = PyPISimple()
sys.meta_path.append(PyPIRemoteFinder(client, package_to_imports={"PIL": "pillow"}))
import PIL.Image

img = PIL.Image.new("RGB", (100, 100), color="red")
img.show()
# p = client.get_project_page("matplotlib")
# dist = choose_best_package(p.packages)
# if dist is None:
#     print("No suitable package found.")
#     exit()
# print(f"Chosen package: {dist.filename} ({dist.url})")
# wheel = RemoteWheelOverHTTP(dist.url)
# loader = PyPIRemoteLoader(wheel)
