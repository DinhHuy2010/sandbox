from shutil import which
from typing import Annotated, Any

from fastapi import Depends

from dhforge.config import Config, read_config
from dhforge.services.git import GitService
from dhforge.services.repositories import RepositoryService

_singletons: dict[str, Any] = {}


def acquire_git_service() -> GitService:
    if "git_service" in _singletons:
        return _singletons["git_service"]
    git_bin = which("git")
    if git_bin is None:
        raise RuntimeError("Git binary not found in PATH")
    s = GitService(binary_location=git_bin)
    _singletons["git_service"] = s
    return s


def acquire_repository_service(
    config: Annotated[Config, Depends(read_config)],
    git_service: Annotated[GitService, Depends(acquire_git_service)],
) -> RepositoryService:
    if "repository_service" in _singletons:
        return _singletons["repository_service"]
    s = RepositoryService(config=config, git=git_service)
    _singletons["repository_service"] = s
    return s
