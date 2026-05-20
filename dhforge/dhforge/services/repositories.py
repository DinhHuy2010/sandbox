import json
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic.dataclasses import dataclass

from dhforge.config import Config
from dhforge.services.exceptions import (
    DHFRepositoryAlreadyExistsError,
    DHFRepositoryNotFoundError,
)
from dhforge.services.git import GitService
from dhforge.logger import get_logger

logger = get_logger().with_tags("repository_service")

# DB = {
#     "hello-world": "~/downloaded_repos/hello-worId.git",
#     "logfire": "~/downloaded_repos/logfire.git",
#     "personal-sandbox": "~/sandbox",
# }


@dataclass
class Repository:
    name: str
    repo_path: Path
    git_service: GitService


@dataclass
class RepositoryService:
    config: Config
    git: GitService
    _index: Any = Field(default=None, init=False)

    def _read_index(self) -> Any:
        if self._index is not None:
            # self._index_cache_hit_counter.add(1)
            return self._index
        index_path = self.config.repositories.index_file.expanduser().resolve()
        try:
            with index_path.open("r") as f:
                self._index = json.load(f)  # Replace with actual parsing logic
                logger.info(f"Loaded repository index from '{index_path}'")
                return self._index
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            raise FileNotFoundError(
                f"Repository index file '{index_path}' not found or inaccessible"
            )

    def _write_index(self, index_data: Any) -> None:
        index_path = self.config.repositories.index_file.expanduser().resolve()
        try:
            with index_path.open("w") as f:
                json.dump(index_data, f)  # Replace with actual serialization logic
                # Invalidate cache after writing
                self._index = None
                logger.info(
                    f"Wrote repository index to '{index_path}' and invalidated cache"
                )
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            raise FileNotFoundError(
                f"Repository index file '{index_path}' not found or inaccessible"
            )

    async def get_repository(self, name: str) -> Repository:
        with logger.span(
            "Finding repository", name=name, _tags=["repository_service.get_repository"]
        ):
            index = self._read_index()
            got = None
            for repo in index["repositories"]:
                if repo["name"] == name:
                    got = repo
                    break
            if got is None:
                raise DHFRepositoryNotFoundError(name=name)
            repo_path = (
                self.config.repositories.repositories_base_dir.expanduser().resolve()
                / got["path"]
            )
            if not repo_path.is_dir():
                raise ValueError(
                    f"Repository path '{repo_path}' does not exist or is not a directory"
                )
            logger.info(f"Found repository '{name}' at path '{repo_path}'")
            return Repository(name=name, repo_path=repo_path, git_service=self.git)

    async def list_repositories(self) -> list[str]:
        with logger.span(
            "Listing repositories", _tags=["repository_service.list_repositories"]
        ) as span:
            index = self._read_index()
            repos = [repo["name"] for repo in index["repositories"]]
            logger.info(f"Found {len(repos)} repositories")
            span.set_attribute("repo_count", len(repos))
            return repos

    async def add_repository(self, name: str) -> Repository:
        with logger.span(
            "Adding repository",
            name=name,
            _tags=["repository_service.add_repository"],
        ) as span:
            if await self.repository_exists(name):
                raise DHFRepositoryAlreadyExistsError(name=name)
            index = self._read_index()
            path = self.config.repositories.repositories_base_dir / name
            try:
                path.mkdir()
            except OSError:
                raise RuntimeError(
                    f"Failed to create directory for repository '{name}' at '{path}'"
                )
            await self.git.init(str(path))
            new_repo = {"name": name, "path": str(path)}
            index["repositories"].append(new_repo)
            self._write_index(index)
            logger.info(f"Added repository '{name}' with path '{path}'")
            span.set_attribute("repo_name", name)
            span.set_attribute("repo_path", str(path))
            return Repository(name=name, repo_path=path, git_service=self.git)

    async def remove_repository(self, name: str) -> None:
        with logger.span(
            "Removing repository",
            name=name,
            _tags=["repository_service.remove_repository"],
        ) as span:
            if not await self.repository_exists(name):
                raise DHFRepositoryNotFoundError(name=name)
            index = self._read_index()
            index["repositories"] = [
                repo for repo in index["repositories"] if repo["name"] != name
            ]
            self._write_index(index)
            logger.info(f"Removed repository '{name}'")
            span.set_attribute("repo_name", name)

    async def repository_exists(self, name: str) -> bool:
        index = self._read_index()
        for repo in index["repositories"]:
            if repo["name"] == name:
                return True
        return False
