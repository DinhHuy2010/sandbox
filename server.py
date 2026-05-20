# pyright: strict

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from functools import cache
from pathlib import Path
from shutil import which
from typing import Annotated

import fastapi
import logfire
from pydantic import BaseModel, EmailStr, Field

logfire.configure(local=True)

app = fastapi.FastAPI()
logfire.instrument_fastapi(app, capture_headers=True)
logfire.instrument_pydantic()

GIT_REPOSITORIES = {"repo1": "~/downloaded_repos/logfire.git"}

repo_router = fastapi.APIRouter(
    prefix="/repositories/{repo_name}", tags=["repositories"]
)


class Commit(BaseModel):
    id: str = Field(description="The commit hash")
    tree: str = Field(description="The tree hash")
    author_name: str = Field(description="The author's name")
    author_email: EmailStr = Field(description="The author's email")
    date: datetime = Field(description="The commit date")
    message: str = Field(description="The commit message")


class Branch(BaseModel):
    name: str = Field(description="The branch name")
    object_id: str = Field(description="The commit hash the branch points to")
    is_head: bool = Field(description="Whether this branch is the current HEAD")


class GitVersion(BaseModel):
    version: str = Field(description="The Git version string")


@dataclass
class GitService:
    git_binary_path: str
    _cached_version: str | None = field(default=None, init=False)

    async def _call_subprocess(self, args: list[str]) -> str:
        with logfire.span("Running git", _level="debug", args=args) as sp:
            p = await asyncio.create_subprocess_exec(
                self.git_binary_path,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logfire.debug(f"Started git with PID: {p.pid}")
            stdout, stderr = await p.communicate()
            if p.returncode != 0:
                logfire.error(f"Git command failed with return code {p.returncode}")
                raise RuntimeError(f"Git command failed: {stderr.strip()}")
            logfire.debug("Git process completed")
            final_stdout = stdout.strip().decode("utf-8")
            final_stderr = stderr.strip().decode("utf-8")
            sp.set_attribute("return_code", p.returncode)
            sp.set_attribute("pid", p.pid)
            sp.set_attribute("stdout", final_stdout)
            sp.set_attribute("stderr", final_stderr)
        return final_stdout

    async def version(self) -> str:
        if self._cached_version is not None:
            return self._cached_version

        with logfire.span("Fetching git version"):
            # Here you would normally run the git command to get the version
            o = await self._call_subprocess(["--version"])
            self._cached_version = o.split()[
                2
            ]  # Assuming output is "git version X.Y.Z"
            logfire.debug(f"Git version fetched: {self._cached_version}")
            return self._cached_version

    async def get_commits(
        self, repo_path: str, n: int = 50, start_from: str | None = None
    ) -> list[Commit]:
        start_from = start_from or "HEAD"
        commits: list[Commit] = []
        with logfire.span(
            f"Fetching {n} commits from {repo_path} starting from {start_from}"
        ) as s:
            # Here you would normally run the git command to get commits
            o = await self._call_subprocess(
                [
                    "-C",
                    repo_path,
                    "log",
                    "-n",
                    str(n),
                    start_from,
                    "--pretty=format:%H%x00%T%x00%an%x00%ae%x00%aI%x00%s",
                ]
            )
            for line in o.split("\n"):
                commit_id, tree, author_name, author_email, date, message = line.split(
                    "\x00"
                )
                commit = Commit(
                    id=commit_id,
                    tree=tree,
                    author_name=author_name,
                    author_email=author_email,
                    date=date,  # type: ignore
                    message=message,
                )
                commits.append(commit)
            logfire.debug(f"Got {len(commits)} commits")
            s.set_attribute("commit_count", len(commits))
            s.set_attribute("commits", [c.id for c in commits])
        return commits

    async def get_branches(self, repo_path: str) -> list[Branch]:
        # repo_path = os.path.expanduser(repo_path)
        with logfire.span(f"Fetching branches from {repo_path}") as b:
            # Here you would normally run the git command to get branches
            o = await self._call_subprocess(
                [
                    "-C",
                    repo_path,
                    "branch",
                    "--list",
                    "--format",
                    '{"refname": "%(refname:short)", "is_head": "%(HEAD)", "object": "%(objectname)"}',
                ]
            )
            branches: list[Branch] = []
            for line in o.split("\n"):
                if not line.strip():
                    continue
                branch = json.loads(line)
                obj = Branch(
                    name=branch["refname"],
                    is_head=branch["is_head"] == "*",
                    object_id=branch["object"],
                )
                branches.append(obj)
            logfire.debug(f"Got {len(branches)} branches")
            b.set_attribute("branch_count", len(branches))
            b.set_attribute("branches", [c.name for c in branches])
        return branches


@cache
def get_git_service(git_bin: str | None = None) -> GitService:
    git_bin = git_bin or which("git")
    if not git_bin:
        logfire.error("Git binary not found in PATH and no git_bin provided")
        raise RuntimeError("Git binary not found")
    logfire.debug(f"Git binary found at: {git_bin}")
    return GitService(git_binary_path=git_bin)


@dataclass
class Repository:
    git_service: GitService
    name: str
    repository_path: Path

    async def get_commits(
        self, n: int = 50, start_from: str | None = None
    ) -> list[Commit]:
        return await self.git_service.get_commits(
            repo_path=str(self.repository_path), n=n, start_from=start_from
        )

    async def get_branches(self):
        # Here you would normally fetch branches from the repository
        # logfire.warning("get_branches is not implemented, returning dummy data")
        # return ["main", "dev", "feature"]
        return await self.git_service.get_branches(repo_path=str(self.repository_path))


def get_repository(repo_name: str) -> Repository:
    if repo_name not in GIT_REPOSITORIES:
        raise fastapi.HTTPException(status_code=404, detail="Repository not found")
    repo_path = GIT_REPOSITORIES[repo_name]
    return Repository(
        name=repo_name,
        repository_path=Path(repo_path).expanduser().resolve(),
        git_service=get_git_service(),
    )


@repo_router.get("/commits")
async def get_commits(
    repo: Annotated[Repository, fastapi.Depends(get_repository)],
) -> list[Commit]:
    return await repo.get_commits()


@repo_router.get("/branches")
async def get_branches(
    repo: Annotated[Repository, fastapi.Depends(get_repository)],
) -> list[Branch]:
    return await repo.get_branches()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/git/version")
async def git_version(
    git_service: Annotated[GitService, fastapi.Depends(get_git_service)],
) -> GitVersion:
    version = await git_service.version()
    return GitVersion(version=version)


@app.get("/")
def read_root():
    return {"Hello": "World"}


app.include_router(repo_router)


def test():
    service = get_git_service()
    # version = service.version()
    # print(f"Git version: {version}")
    repo_path = Path("~/downloaded_repos/logfire.git/").expanduser()
    commits = service.get_commits(repo_path=str(repo_path), n=5)
    print(commits)


if __name__ == "__main__":
    test()
