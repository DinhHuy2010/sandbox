from __future__ import annotations


import asyncio
from functools import cached_property
import os
import subprocess
from pathlib import Path
from typing import IO, Any

from pydantic import Field
from pydantic.dataclasses import dataclass

from dhforge.logger import get_logger
from dhforge.models.git import Author, Reference, Commit
from dhforge.services.exceptions import DHFGitCommandError

logger = get_logger().with_tags("git_service")

_COMMIT_LOG_FORMAT = "%H%x00%an%x00%ae%x00%aI%x00%s"


@dataclass
class GitCommitsService:
    git_service: "GitService"

    async def list(
        self, repo_path: str | Path, count: int = 10, start_from: str | None = None
    ) -> list[Commit]:
        with logger.span(
            "Retrieving git commits",
            repo_path=repo_path,
            count=count,
            start_from=start_from,
            _tags=["git_service.commits"],
            _level="debug",
        ) as span:
            args = [
                "log",
                f"-n{count}",
                "--pretty=format:%H%x00%an%x00%ae%x00%aI%x00%s",
            ]
            if start_from:
                args.append(start_from)
            output = await self.git_service.call(*args, cwd=repo_path)
            commits = []
            for line in output.strip().split("\n"):
                parts = line.split("\x00")
                if len(parts) == 5:
                    commits.append(
                        Commit(
                            hash=parts[0],
                            author=Author(name=parts[1], email=parts[2]),
                            date=parts[3],  # type: ignore
                            message=parts[4],
                        )
                    )
                else:
                    logger.warning(
                        f"Unexpected commit format: {line}",
                        _tags=["git_service.commits"],
                    )
            logger.info(f"Retrieved {len(commits)} commits from {repo_path}")
            span.set_attribute("commit_count", len(commits))
            return commits


@dataclass
class GitRefsService:
    git_service: "GitService"

    async def list(self, repo_path: str | Path) -> list[Reference]:
        with logger.span(
            "Retrieving git refs",
            repo_path=repo_path,
            _tags=["git_service.refs"],
            _level="debug",
        ) as span:
            output = await self.git_service.call("show-ref", cwd=repo_path)
            refs = []
            for line in output.strip().split("\n"):
                parts = line.split()
                if len(parts) == 2:
                    refs.append(Reference(name=parts[1], object_hash=parts[0]))
                else:
                    logger.warning(
                        f"Unexpected ref format: {line}",
                        _tags=["git_service.refs"],
                    )
            logger.info(f"Retrieved {len(refs)} refs from {repo_path}")
            span.set_attribute("ref_count", len(refs))
            return refs

    async def create(self, repo_path: str | Path, ref_name: str, target: str) -> None:
        with logger.span(
            "Creating git ref",
            repo_path=repo_path,
            ref_name=ref_name,
            target=target,
            _tags=["git_service.refs.create"],
            _level="debug",
        ):
            await self.git_service.call("update-ref", ref_name, target, cwd=repo_path)
            logger.info(f"Created git ref {ref_name} pointing to {target}")

    async def delete(self, repo_path: str | Path, ref_name: str) -> None:
        with logger.span(
            "Deleting git ref",
            repo_path=repo_path,
            ref_name=ref_name,
            _tags=["git_service.refs.delete"],
            _level="debug",
        ):
            await self.git_service.call("update-ref", "-d", ref_name, cwd=repo_path)
            logger.info(f"Deleted git ref {ref_name}")


@dataclass
class GitBranchesService:
    git_service: "GitService"

    async def create(
        self, repo_path: str | Path, branch_name: str, start_point: str | None = None
    ) -> None:
        if start_point is None:
            start_point = "HEAD"
        with logger.span(
            "Creating git branch",
            repo_path=repo_path,
            branch_name=branch_name,
            start_point=start_point,
            _tags=["git_service.branches.create"],
            _level="debug",
        ):
            await self.git_service.refs.create(
                repo_path, f"refs/heads/{branch_name}", start_point
            )
            logger.info(f"Created branch {branch_name} at {start_point}")

    async def delete(self, repo_path: str | Path, branch_name: str) -> None:
        with logger.span(
            "Deleting git branch",
            repo_path=repo_path,
            branch_name=branch_name,
            _tags=["git_service.branches.delete"],
            _level="debug",
        ):
            await self.git_service.refs.delete(repo_path, f"refs/heads/{branch_name}")
            logger.info(f"Deleted branch {branch_name}")

    async def list(self, repo_path: str | Path) -> list[Reference]:
        with logger.span(
            "Retrieving git branches",
            repo_path=repo_path,
            _tags=["git_service.branches"],
            _level="debug",
        ):
            refs = await self.git_service.refs.list(repo_path)
            branches = [ref for ref in refs if ref.is_branch]
            logger.info(f"Retrieved {len(branches)} branches from {repo_path}")
            return branches


@dataclass
class GitService:
    """
    Perform git operations by calling the git binary directly.
    This service is designed to be used in a local environment where the git binary is available.
    """

    binary_location: str = Field(
        ..., description="The location of the git binary on the system"
    )
    _cache: dict[str, Any] = Field(default_factory=dict, init=False)

    async def call(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
        stdin: IO[bytes] | None = None,
    ) -> str:
        """Executes a git command with the given arguments and returns the output as a string."""
        with logger.span(
            "Running git command",
            args=args,
            env=env,
            cwd=cwd,
            _tags=["git_service.subprocess_call"],
            _level="debug",
        ):
            process = await asyncio.create_subprocess_exec(
                self.binary_location,
                *args,
                env={**os.environ, **(env or {})},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                stdin=stdin,
            )
            logger.debug(f"Started git process with PID {process.pid}")
            stdout, stderr = await process.communicate()
            if process.returncode is not None and process.returncode != 0:
                raise DHFGitCommandError(
                    binary_location=self.binary_location,
                    command_args=list(args),
                    stderr=stderr.decode(),
                    exit_code=process.returncode,
                    pid=process.pid,
                )
            return stdout.decode()

    async def version(self) -> str:
        if "version" in self._cache:
            return self._cache["version"]

        with logger.span(
            "Retrieving git version", _tags=["git_service.version"], _level="debug"
        ):
            version_output = await self.call("--version")
            version = version_output.strip().split()[-1]
            self._cache["version"] = version
            logger.info(f"Git version retrieved: {version}")
            return version

    async def init(self, path: str | Path) -> None:
        with logger.span(
            "Initializing git repository",
            path=path,
            _tags=["git_service.init_repository"],
            _level="debug",
        ):
            await self.call("init", cwd=path)
            logger.info(f"Initialized git repository at {path}")

    @cached_property
    def commits(self) -> GitCommitsService:
        return GitCommitsService(git_service=self)

    @cached_property
    def refs(self) -> GitRefsService:
        return GitRefsService(git_service=self)

    @cached_property
    def branches(self) -> GitBranchesService:
        return GitBranchesService(git_service=self)

    async def diff(self, repo_path: str | Path, commit_a: str, commit_b: str) -> str:
        with logger.span(
            "Retrieving git diff",
            repo_path=repo_path,
            commit_a=commit_a,
            commit_b=commit_b,
            _tags=["git_service.diff"],
            _level="debug",
        ) as span:
            output = await self.call("diff", f"{commit_a}..{commit_b}", cwd=repo_path)
            logger.info(f"Retrieved git diff between {commit_a} and {commit_b}")
            span.set_attribute("diff_length", len(output))
            return output
