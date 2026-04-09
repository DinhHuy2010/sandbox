# pyright: strict

from base64 import b64decode, b64encode
from pathlib import Path
import sys
import zipfile
from contextlib import contextmanager
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
from importlib.metadata import (
    Distribution,
    DistributionFinder,
    PackageNotFoundError,
)
from typing import Any, Generator
from warnings import warn

import orjson
from packaging.requirements import Requirement
from packaging.tags import sys_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version
from pypi_simple import DistributionPackage, PyPISimple
from remotezip import RemoteZip  # pyright: ignore[reportMissingTypeStubs]

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


def is_suitable_package(pkg: DistributionPackage, options: "Options") -> bool:
    if pkg.package_type != "wheel":
        return False
    requirement = options.requirements_mapping.get(
        canonicalize_name(pkg.project),  # type: ignore
        Requirement(pkg.project),  # type: ignore
    )
    if not requirement.specifier.contains(
        pkg.version,  # type: ignore
        prereleases=options.include_prereleases,
    ):
        return False
    return best_tag_rank(pkg) is not None


def choose_best_package(
    packages: list[DistributionPackage], options: "Options | None" = None
) -> DistributionPackage | None:
    if not packages:
        return None

    if options is None:
        options = Options()

    def build_candidates() -> Generator[
        tuple[DistributionPackage, Version, int | None, datetime | None], None, None
    ]:
        for p in packages:
            if p.project is None:
                continue
            if p.version is None:
                continue
            if is_suitable_package(p, options):
                yield ((p, Version(p.version), best_tag_rank(p), p.upload_time))

    out = max(build_candidates(), key=lambda p: p[1:], default=None)
    if out is None:
        return None
    return out[0]


def _discover_dist_info_path(zf: RemoteZip) -> zipfile.Path | None:
    return next((p for p in zipfile.Path(zf).glob("*.dist-info") if p.is_dir()), None)


@dataclass
class Options:
    enumerate_everything: bool = False
    requirements_mapping: dict[str, Requirement] = field(
        default_factory=dict[str, Requirement]
    )
    include_prereleases: bool = False
    enumerate_only_packages: list[str] | None = field(default=None)
    cache: "Cache" = field(default_factory=lambda: Cache())


@dataclass(repr=False)
class PyPIRepositoryDistribution(Distribution):
    pypi_simple: PyPISimple
    package: DistributionPackage
    raw_metadata_content: bytes | None = field(default=None)
    _wheel_zf: RemoteZip | None = field(default=None, init=False)

    def __repr__(self):
        pkg = self.package.project
        version = self.package.version
        return f"<PyPIRepositoryDistribution {pkg}=={version} from {self.pypi_simple.endpoint!r}>"

    def _get_metadata(self) -> bytes:
        if self.raw_metadata_content is None:
            self.raw_metadata_content = self.pypi_simple.get_package_metadata_bytes(
                self.package
            )
        return self.raw_metadata_content

    @property
    def name(self) -> str:
        assert self.package.project is not None
        return self.package.project

    @property
    def version(self) -> str:
        assert self.package.version is not None
        return self.package.version

    def _open_wheel(self) -> RemoteZip:
        if self._wheel_zf is None:
            self._wheel_zf = RemoteZip(self.package.url, support_suffix_range=False)
            self._wheel_zf.filename = self.package.filename
        return self._wheel_zf

    def read_text(self, filename: str) -> str | None:
        if filename in {"METADATA", "PKG-INFO"}:
            metadata_bytes = self._get_metadata()
            return metadata_bytes.decode("utf-8")
        zf = self._open_wheel()
        try:
            dist_info_path = _discover_dist_info_path(zf)
            if dist_info_path is None:
                return None
            meta_loc = dist_info_path / filename
            return meta_loc.read_text()
        except (KeyError, FileNotFoundError):
            return None

    def locate_file(self, path: Any) -> zipfile.Path:  # type: ignore
        zf = self._open_wheel()
        try:
            p = zipfile.Path(zf)
            return p / path
        except (KeyError, FileNotFoundError):
            raise FileNotFoundError(f"File {path!r} not found in the wheel") from None

    def __enter__(self) -> "PyPIRepositoryDistribution":
        return self

    def __exit__(self, *_) -> None:
        if self._wheel_zf is not None:
            self._wheel_zf.close()
            self._wheel_zf = None


@dataclass
class Cache:
    cache_dir: Path = field(default_factory=lambda: Path(".pypi_cache"))
    ttl: int = 3600

    def evict_when_stale(self) -> None:
        now = datetime.now().timestamp()
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.is_file():
                if now - cache_file.stat().st_mtime > self.ttl:
                    cache_file.unlink()

    def store(self, dist: DistributionPackage, metadata: bytes) -> None:
        assert dist.project is not None
        self.evict_when_stale()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self.cache_dir / f"{canonicalize_name(dist.project)}.json"
        if cache_path.is_file():
            return
        cache_path.write_bytes(
            orjson.dumps(
                {"info": dist, "metadata": b64encode(metadata).decode("ascii")},
                option=orjson.OPT_SERIALIZE_DATACLASS | orjson.OPT_INDENT_2,
            )
        )

    def load(self, name: str) -> tuple[DistributionPackage, bytes] | None:
        self.evict_when_stale()
        cache_path = self.cache_dir / f"{canonicalize_name(name)}.json"
        if not cache_path.is_file():
            return None
        try:
            data = orjson.loads(cache_path.read_bytes())
            dist = DistributionPackage(**data["info"])
            metadata = b64decode(data["metadata"])
            return dist, metadata
        except Exception:
            return None

    def invalidate(self, name: str) -> None:
        cache_path = self.cache_dir / f"{canonicalize_name(name)}.json"
        if cache_path.is_file():
            cache_path.unlink()

    def invalidate_all(self) -> None:
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.is_file():
                cache_file.unlink()


@dataclass
class PyPIPackageResolver:
    pypi_simple: PyPISimple
    options: Options
    cache: Cache

    def resolve(self, name: str) -> tuple[DistributionPackage, bytes]:
        if (cached := self.cache.load(name)) is not None:
            print(f"Cache hit for {name!r}, using cached metadata")  # type: ignore
            return cached
        project = self.pypi_simple.get_project_page(name)
        if not project:
            raise PackageNotFoundError(name)
        package = choose_best_package(project.packages, self.options)
        if package is None:
            raise RuntimeError(
                f"No suitable package found for {name!r} on this currently running interpreter"
            )
        metadata = self.pypi_simple.get_package_metadata_bytes(package)
        self.cache.store(package, metadata)
        return package, metadata

    def enumerate_all_packages(
        self,
    ) -> Generator[tuple[DistributionPackage, bytes], None, None]:
        def get_project_stream():
            if self.options.enumerate_everything:
                return self.pypi_simple.stream_project_names()
            elif self.options.enumerate_only_packages is not None:
                return iter(self.options.enumerate_only_packages)
            else:
                warn(
                    "Enumerating all distributions from a PyPI repository is disabled. Set Options.enumerate_everything to True to enable this behavior.",
                    UserWarning,
                    stacklevel=2,
                )
                return iter([])

        for project in get_project_stream():
            try:
                yield self.resolve(project)
            except (PackageNotFoundError, RuntimeError):
                continue


class PyPIRepositoryDistributionFinder(DistributionFinder):
    def __init__(
        self, pypi_simple: PyPISimple | None = None, options: Options | None = None
    ):
        super().__init__()
        self._pypi_simple = pypi_simple or PyPISimple()
        self._options = options or Options()
        self._resolver = PyPIPackageResolver(
            self._pypi_simple, self._options, self._options.cache
        )

    def find_spec(self, *args: Any, **kwargs: Any) -> None:
        return None

    def find_distributions(
        self, context: DistributionFinder.Context | None = None
    ) -> Generator[PyPIRepositoryDistribution, None, None]:
        if context is None:
            context = DistributionFinder.Context()
        if context.name is not None:
            package = self._resolver.resolve(context.name)
            yield PyPIRepositoryDistribution(self._pypi_simple, *package)
        else:
            for package in self._resolver.enumerate_all_packages():
                yield PyPIRepositoryDistribution(self._pypi_simple, *package)


default = PyPIRepositoryDistributionFinder()


@contextmanager
def configure_finder(
    pypi_simple: PyPISimple | None = None,
    options: Options | None = None,
    install_to_meta_path: bool = False,
    set_as_default: bool = False,
) -> Generator[PyPIRepositoryDistributionFinder, None, None]:
    global default
    if install_to_meta_path and set_as_default:
        raise ValueError(
            "Cannot set as default and install to meta path at the same time"
        )
    finder = PyPIRepositoryDistributionFinder(pypi_simple=pypi_simple, options=options)
    orig = copy(default)
    if install_to_meta_path:
        sys.meta_path.append(finder)
    elif set_as_default:
        default = finder
    try:
        yield finder
    finally:
        if install_to_meta_path:
            sys.meta_path.remove(finder)
        elif set_as_default:
            default = orig


def distribution(name: str) -> PyPIRepositoryDistribution:
    try:
        return next(default.find_distributions(DistributionFinder.Context(name=name)))
    except PackageNotFoundError:
        raise
    except StopIteration:
        raise PackageNotFoundError(name) from None


def distributions() -> Generator[PyPIRepositoryDistribution, None, None]:
    yield from default.find_distributions()


def main() -> None:
    from importlib.metadata import distributions

    with configure_finder(
        PyPISimple("https://pypi.org/simple/"),
        options=Options(
            requirements_mapping={
                "uv": Requirement("uv<0.7.0"),
                # "pydantic": Requirement("pydantic<2.0.0"),
            },
            # enumerate_everything=True,
            enumerate_only_packages=["fastapi", "uv", "pydantic"],
            cache=Cache(ttl=600),
        ),
        install_to_meta_path=True,
    ):
        for dist in distributions():
            print(dist.requires)


if __name__ == "__main__":
    main()
