from importlib.metadata import (
    DistributionFinder,
    PathDistribution,
    distribution,
)
from pathlib import Path
import sys
from typing import Sequence
from zipfile import ZipFile, Path as ZipPath


import anyio
from attrs import define, field
import fsspec
import packaging
import packaging.metadata
from packaging.specifiers import SpecifierSet
from packaging.tags import sys_tags
from packaging.utils import (
    InvalidWheelFilename,
    canonicalize_name,
    parse_wheel_filename,
)

# import requests
from simple_repository import SimpleRepository
from simple_repository.components.http_cached import CachedHttpRepository
from simple_repository.model import File

# logging.getLogger("urllib3").setLevel(logging.NOTSET)


def best_wheel_for_system(
    wheel_files: list[str],
    *,
    project_name: str | None = None,
) -> str | None:
    supported = list(sys_tags())
    tag_rank = {tag: i for i, tag in enumerate(supported)}

    best: tuple[object, int, tuple, str] | None = None
    best_file: str | None = None

    for wheel in wheel_files:
        filename = Path(wheel).name

        try:
            name, version, build, wheel_tags = parse_wheel_filename(filename)
        except InvalidWheelFilename:
            continue

        if project_name is not None:
            if canonicalize_name(str(name)) != canonicalize_name(project_name):
                continue

        ranks = [tag_rank[tag] for tag in wheel_tags if tag in tag_rank]
        if not ranks:
            continue

        # Higher version is better.
        # Lower tag rank is better.
        # Higher build tag is better.
        score = (version, -min(ranks), build or ())

        if best is None or score > best:
            best = score
            best_file = wheel

    return best_file


http: fsspec.AbstractFileSystem = fsspec.filesystem("http")


class RemoteWheelDistribution(PathDistribution):
    """A distribution that is backed by a remote wheel file."""

    def __init__(self, url: str):
        self._hfile = http.open(url)
        # self._hfile = fsspec.filesystem(url)
        self._zip = ZipFile(self._hfile)
        self._zip_path = ZipPath(self._zip)
        self._dist_location = next(self._zip_path.glob("*.dist-info"))
        super().__init__(self._dist_location)


def _filter_files(
    files: Sequence[File], allow_prerelases: bool, constraint: "Constraint | None"
) -> dict[str, File]:
    fdict: dict[str, File] = {}
    specifier = None
    if constraint is not None:
        specifier = SpecifierSet(constraint.specifier)
    for f in files:
        try:
            name, version, *_ = parse_wheel_filename(f.filename)
        except InvalidWheelFilename:
            continue
        if f.yanked:
            continue
        if not allow_prerelases and version.is_prerelease:
            continue
        if specifier is not None and not specifier.contains(
            version, prereleases=allow_prerelases
        ):
            continue
        fdict[f.filename] = f

    return fdict


@define
class Constraint:
    specifier: str


@define
class RepositoryFinder(DistributionFinder):
    repository: SimpleRepository
    enabled: bool = True
    allow_prereleases: bool = False
    constraints: dict[str, Constraint] = field(
        factory=dict,
        converter=lambda d: {canonicalize_name(k): v for k, v in d.items()},
    )

    def find_distributions(self, context: DistributionFinder.Context | None = None):
        if not self.enabled:
            return []
        if context.name is None:
            return []
        name = context.name
        dist = anyio.run(self.repository.get_project_page, name)
        files = _filter_files(
            dist.files,
            self.allow_prereleases,
            self.constraints.get(canonicalize_name(name)),
        )
        file = best_wheel_for_system(list(files.keys()))
        if file is None:
            return []
        # name, version, *_ = parse_wheel_filename(file)
        return [RemoteWheelDistribution(files[file].url)]
        # return super().find_distributions(context)


# some mirror found off the internet
# MIRROR = "https://mirrors.sustech.edu.cn/pypi/web/simple"
MIRROR = "https://pypi.org/simple/"

finder = RepositoryFinder(
    CachedHttpRepository(MIRROR, Path("./.cache/simple-repository")),
    enabled=True,
    constraints={
        "boto3": Constraint("==1.28.0"),
        # "PyGitHub": Constraint("<2.0.0"),
    },  # for testing
)
sys.meta_path.insert(0, finder)
# sys.meta_path.append(finder)
dist = distribution("rich")
print(f"{dist.name}=={dist.version}")
print(packaging.metadata.RawMetadata(dist.metadata)["Summary"])
