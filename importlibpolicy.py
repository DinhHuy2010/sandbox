# pyright: standard

import importlib.abc
import importlib.machinery
import inspect
import sys
from dataclasses import dataclass


@dataclass
class UnresolveModule:
    module_file: str | None = None


@dataclass
class ResolvedModule:
    module_file: str | None = None


@dataclass
class Importer:
    origin_type: str
    module_name: str | None
    file: str | None


@dataclass
class ImportRequest:
    module_name: str
    module_source: UnresolveModule
    importer: Importer


@dataclass
class ImportResponse:
    desicion: str
    request: ImportRequest
    resolved: ResolvedModule


class PolicyFinder(importlib.abc.MetaPathFinder):
    def _get_importer(self):
        frame = inspect.currentframe()
        if frame is None:
            return None, None

        frame = frame.f_back
        while frame:
            g = frame.f_globals
            name = g.get("__name__")
            file = g.get("__file__")
            if name not in {
                __name__,
                "importlib._bootstrap",
                "importlib._bootstrap_external",
            }:
                return name, file
            frame = frame.f_back
        return None, None

    def find_spec(self, fullname, path=None, target=None):
        importer_name, importer_file = self._get_importer()
        print(f"{importer_name=} {importer_file=} importing {fullname}")
        return None


sys.meta_path.insert(0, PolicyFinder())


import httpx
