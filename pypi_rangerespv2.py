import asyncio
from importlib.metadata import PathDistribution
from pathlib import Path
from zipfile import ZipFile, Path as ZipPath

from packaging.tags import Tag, sys_tags
from packaging.utils import parse_wheel_filename
from packaging.version import Version
from simple_repository.components.http_cached import CachedHttpRepository
from simple_repository.model import File

from rangerespv2 import HTTPFile


SYS_TAGS_ORDERED = tuple(sys_tags())
SYS_TAG_RANK = {tag: i for i, tag in enumerate(SYS_TAGS_ORDERED)}


def best_tag_rank(tags: tuple[Tag, ...]) -> int | None:
    best: int | None = None
    for tag in tags:
        rank = SYS_TAG_RANK.get(tag)
        if rank is not None and (best is None or rank < best):
            best = rank
    return best


def is_suitable_package(pkg: File) -> bool:
    try:
        *_, tags = parse_wheel_filename(pkg.filename)
    except Exception:
        return False
    return best_tag_rank(tags) is not None


def choose_best_package(packages: list[File], latest_version: Version) -> File | None:
    def build_candidates():
        for pkg in packages:
            if not is_suitable_package(pkg):
                continue
            try:
                _, version, _, tags = parse_wheel_filename(pkg.filename)
            except Exception:
                continue
            if version != latest_version:
                continue
            rank = best_tag_rank(tags)
            if rank is not None:
                yield rank, pkg

    return max(build_candidates(), default=(None, None), key=lambda x: x[0])[1]


async def main():
    repository = CachedHttpRepository(
        "https://pypi.org/simple/", Path(".cache/simple-repository")
    )
    package = await repository.get_project_page("requests")
    version = Version(max(package.versions, key=Version))
    pkg = choose_best_package(package.files, version)
    url = pkg.url
    with HTTPFile(url) as f:
        with ZipFile(f) as zf:
            zp = ZipPath(zf)
            di = next(zp.glob("*.dist-info"))
            dist = PathDistribution(di)
            print(dist.locate_file("requests/__init__.py").read_text())


if __name__ == "__main__":
    asyncio.run(main())
