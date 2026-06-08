"""Context for the installer."""

from __future__ import annotations

from attrs import define
from packaging.version import Version

from dhinstaller.environments import Environment


@define
class RepositoryContext:
    """Context for repository interactions."""

    url: str
    """URL of the repository being interacted with."""


@define
class InstallerContext:
    """Context for the installer."""

    name: str
    """Package name being installed."""
    version: Version
    """Package version being installed."""
    env: Environment
    """Environment into which the package is being installed."""
    repository: RepositoryContext
    """Context for the repository from which the package is being installed."""
