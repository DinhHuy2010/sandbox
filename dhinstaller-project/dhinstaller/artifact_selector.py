"""Select the most suitable package artifact for a target environment."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from packaging.specifiers import SpecifierSet
from packaging.tags import Tag, compatible_tags, cpython_tags, platform_tags
from packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    parse_sdist_filename,
    parse_wheel_filename,
)
from packaging.version import Version
from simple_repository.model import File

if TYPE_CHECKING:
    from dhinstaller.environments import Environment


def supported_tags_for_python(major: int, minor: int):
    """Build supported packaging tags for a Python version.

    Parameters
    ----------
    major
        Python major version.
    minor
        Python minor version.

    Returns
    -------
    list[packaging.tags.Tag]
        Compatible wheel tags ordered from most preferred to least preferred.
    """
    platforms = list(platform_tags())
    tags = list(cpython_tags(python_version=(major, minor), platforms=platforms))
    tags += list(compatible_tags(python_version=(major, minor), platforms=platforms))  # noqa: F821
    return tags


def artifact_sort_key(
    file: File, tags_ranks: dict[Tag, int]
) -> tuple[Version | None, int, int, tuple, str]:
    """Return a sort key that ranks artifacts by version and compatibility.

    Parameters
    ----------
    file
        Artifact metadata to rank.
    tags_ranks
        Mapping from supported wheel tags to preference ranks.

    Returns
    -------
    tuple[packaging.version.Version | None, int, int, tuple, str]
        Sort key containing version, artifact kind preference, tag preference,
        wheel build tag, and filename.
    """
    filename = file.filename

    # 1. Compatible wheel
    try:
        _, version, build, wheel_tags = parse_wheel_filename(filename)
        ranks = [tags_ranks[tag] for tag in wheel_tags if tag in tags_ranks]
        if ranks:
            return (
                version,
                1,  # wheel beats sdist
                -min(ranks),  # better wheel tag
                build or (),
                filename,
            )
    except InvalidWheelFilename:
        pass

    # 2. Source distribution
    try:
        _, version = parse_sdist_filename(filename)
    except InvalidSdistFilename:
        version = None
    return (
        version,
        0,  # sdist below wheel
        0,
        (),
        filename,
    )


def distriution_type(filename: str) -> Literal["wheel", "sdist", "unknown"]:
    """Determine the distribution type represented by a filename.

    Parameters
    ----------
    filename
        Artifact filename to inspect.

    Returns
    -------
    {"wheel", "sdist", "unknown"}
        Distribution type inferred from the filename.
    """
    try:
        parse_wheel_filename(filename)
        return "wheel"
    except InvalidWheelFilename:
        pass

    try:
        parse_sdist_filename(filename)
        return "sdist"
    except InvalidSdistFilename:
        pass

    return "unknown"


def find_best_artifacts(
    env: Environment,
    files: Sequence[File],
    version_constraints: SpecifierSet | None = None,
) -> tuple[File, str]:
    """Find the best artifact for an environment and optional version constraint.

    Parameters
    ----------
    env
        Target Python environment.
    files
        Candidate package artifacts.
    version_constraints
        Optional specifier set limiting acceptable versions.

    Returns
    -------
    tuple[simple_repository.model.File | None, str]
        Best artifact and its distribution type, or ``(None, "unknown")`` when
        no compatible artifact is found.
    """
    major, minor, *_ = env.version_tuple
    supported = supported_tags_for_python(major, minor)
    tags_ranks = {t: i for i, t in enumerate(supported, start=1)}

    files_by_version: dict[Version, list[tuple[File, str]]] = {}

    for file in files:
        version, *_ = artifact_sort_key(file, tags_ranks)
        if version is None:
            continue
        files_by_version.setdefault(version, []).append(
            (file, distriution_type(file.filename))
        )

    best_files_by_versions = {
        version: max(files, key=lambda x: artifact_sort_key(x[0], tags_ranks))
        for version, files in files_by_version.items()
    }
    if version_constraints is not None:
        best_files_by_versions = {
            version: file_info
            for version, file_info in best_files_by_versions.items()
            if version in version_constraints
        }
    best_known_version = max(best_files_by_versions.keys(), default=None)
    if best_known_version is None:
        return None, "unknown"
    return best_files_by_versions[best_known_version]
