from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path as FastAPIPath, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from dhforge.services.repositories import (
    Repository,
    RepositoryService,
)
from dhforge.services.git import Commit, Reference
from dhforge.logger import get_logger
from dhforge.services.exceptions import (
    DHFRepositoryNotFoundError as RepositoryNotFoundError,
)

from dhforge.services.deps import acquire_repository_service

logger = get_logger()
repositories_router = APIRouter(prefix="/repositories", tags=["repositories"])
per_repository_router = APIRouter(prefix="/{name}", tags=["repository"])


class RepositoryListResponseModel(BaseModel):
    """Response model for listing repositories."""

    repositories: list[str] = Field(
        ...,
        description="A list of registered repository names",
        examples=[["repo1", "repo2"]],
    )


class RepositoryCreateRequestModel(BaseModel):
    """Request model for creating a new repository."""

    name: str = Field(
        ..., description="The name of the repository to add", examples=["my-repo"]
    )
    path: Path = Field(
        ...,
        description="The filesystem path to the repository",
        examples=["/path/to/repo"],
    )


class RepositoryCreateOKResponseModel(BaseModel):
    """Response model for a successful repository creation."""

    message: str = Field(
        ..., description="A message indicating the result of the repository creation"
    )
    name: str = Field(
        ...,
        description="The name of the newly created repository",
        examples=["my-repo"],
    )
    path: Path = Field(
        ...,
        description="The filesystem path to the newly created repository",
        examples=["/path/to/repo"],
    )


class RepositoryGetResponseModel(BaseModel):
    """Response model for retrieving repository details."""

    name: str = Field(
        ..., description="The name of the repository", examples=["my-repo"]
    )
    path: Path = Field(
        ...,
        description="The filesystem path to the repository",
        examples=["/path/to/repo"],
    )


class RepositoryUpdateRequestModel(BaseModel):
    """Request model for updating a repository's path."""

    new_path: Path = Field(
        ...,
        description="The new filesystem path for the repository",
        examples=["/new/path/to/repo"],
    )


class RepositoryDeleteResponseModel(BaseModel):
    """Response model for a successful repository deletion."""

    message: str = Field(
        ..., description="A message indicating the result of the repository deletion"
    )


class RepositoryCommitsResponseModel(BaseModel):
    """Response model for retrieving recent commits of a repository."""

    commits: list[Commit] = Field(
        ..., description="A list of recent commits in the repository"
    )


class RepositoryBranchesResponseModel(BaseModel):
    """Response model for retrieving branches of a repository."""

    branches: list[Reference] = Field(
        ..., description="A list of branches in the repository"
    )


class RepositoryBranchCreateRequestModel(BaseModel):
    """Request model for creating a new branch in a repository."""

    branch_name: str = Field(
        ...,
        description="The name of the new branch to create",
        examples=["feature/new-feature"],
    )
    start_point: str = Field(
        ...,
        description="The commit hash or reference to start the new branch from",
        examples=["HEAD", "main", "7f3a9c2b8e4d6f1a0c9b5d3e2f8a6b4c1d0e9f7a"],
    )


class RepositoryBranchCreateResponseModel(BaseModel):
    """Response model for a successful branch creation."""

    message: str = Field(
        ..., description="A message indicating the result of the branch creation"
    )
    branch_name: str = Field(
        ...,
        description="The name of the newly created branch",
        examples=["feature/new-feature"],
    )
    start_point: str = Field(
        ...,
        description="The commit hash or reference the new branch was created from",
        examples=["HEAD", "main", "7f3a9c2b8e4d6f1a0c9b5d3e2f8a6b4c1d0e9f7a"],
    )


class RepositoryBranchDeleteResponseModel(BaseModel):
    """Response model for a successful branch deletion."""

    message: str = Field(
        ..., description="A message indicating the result of the branch deletion"
    )


async def acquire_repository(
    service: Annotated[RepositoryService, Depends(acquire_repository_service)],
    name: Annotated[str, FastAPIPath(..., description="The name of the repository")],
) -> Repository:
    try:
        return await service.get_repository(name)
    except RepositoryNotFoundError:
        raise HTTPException(status_code=404, detail=f"Repository '{name}' not found")


@repositories_router.get(
    "", response_model=RepositoryListResponseModel, summary="List repositories"
)
async def list_repositories(
    repository_service: Annotated[
        RepositoryService, Depends(acquire_repository_service)
    ],
):
    """Endpoint to list all registered repositories."""
    # Placeholder implementation
    repos = await repository_service.list_repositories()
    return {"repositories": repos}


@repositories_router.post(
    "",
    response_model=RepositoryCreateOKResponseModel,
    status_code=201,
    summary="Add a new repository",
)
async def add_repository(
    request: RepositoryCreateRequestModel,
    repository_service: Annotated[
        RepositoryService, Depends(acquire_repository_service)
    ],
):
    """Endpoint to add a new repository."""
    # Placeholder implementation
    existed = await repository_service.repository_exists(request.name)
    if existed:
        raise HTTPException(
            status_code=400, detail=f"Repository '{request.name}' already exists"
        )
    repo = await repository_service.add_repository(request.name)
    return {
        "message": f"Repository '{request.name}' added successfully",
        "path": str(repo.repo_path),
    }


@per_repository_router.get(
    "",
    response_model=RepositoryGetResponseModel,
    summary="Get repository details",
)
async def get_repository(repo: Annotated[Repository, Depends(acquire_repository)]):
    """Endpoint to retrieve details of a specific repository."""
    # Placeholder implementation
    return RepositoryGetResponseModel(name=repo.name, path=repo.repo_path)


@per_repository_router.delete(
    "",
    response_model=RepositoryDeleteResponseModel,
    summary="Delete a repository",
)
async def delete_repository(
    name: str,
    repository_service: Annotated[
        RepositoryService, Depends(acquire_repository_service)
    ],
):
    """Endpoint to delete a specific repository."""
    # Placeholder implementation
    try:
        await repository_service.remove_repository(name)
        return {"message": f"Repository '{name}' deleted successfully"}
    except RepositoryNotFoundError:
        raise HTTPException(status_code=404, detail=f"Repository '{name}' not found")


@per_repository_router.get(
    "/commits",
    response_model=RepositoryCommitsResponseModel,
    summary="Get recent commits of a repository",
)
async def get_repository_commits(
    repo: Annotated[Repository, Depends(acquire_repository)],
    count: Annotated[
        int, Query(description="The number of commits to retrieve", gt=0)
    ] = 10,
    start_from: str | None = None,
):
    """Endpoint to retrieve recent commits from a specific repository."""
    # Placeholder implementation
    commits = await repo.git_service.commits.list(
        repo.repo_path, count=count, start_from=start_from
    )
    return {"commits": commits}


@per_repository_router.get(
    "/branches",
    response_model=RepositoryBranchesResponseModel,
    summary="Get branches of a repository",
)
async def get_repository_branches(
    repo: Annotated[Repository, Depends(acquire_repository)],
):
    """Endpoint to retrieve branches from a specific repository."""
    # Placeholder implementation
    branches = await repo.git_service.branches.list(repo.repo_path)
    return {"branches": branches}


@per_repository_router.get(
    "/diff/{commit_a}/{commit_b}",
    response_class=PlainTextResponse,
    summary="Get diff between two commits of a repository",
)
async def get_repository_diff(
    repo: Annotated[Repository, Depends(acquire_repository)],
    commit_a: Annotated[
        str, FastAPIPath(..., description="The hash or reference of the first commit")
    ],
    commit_b: Annotated[
        str, FastAPIPath(..., description="The hash or reference of the second commit")
    ],
) -> str:
    """Endpoint to retrieve the diff between two commits in a specific repository."""
    # Placeholder implementation
    diff = await repo.git_service.diff(repo.repo_path, commit_a, commit_b)
    return diff


@per_repository_router.post(
    "/branches",
    summary="Create a new branch in a repository",
    response_model=RepositoryBranchCreateResponseModel,
)
async def create_branch(
    repo: Annotated[Repository, Depends(acquire_repository)],
    form: RepositoryBranchCreateRequestModel,
):
    """Endpoint to create a new branch in a specific repository."""
    # Placeholder implementation
    await repo.git_service.branches.create(
        repo.repo_path, form.branch_name, form.start_point
    )
    return {
        "message": f"Branch '{form.branch_name}' created successfully",
        "branch_name": form.branch_name,
        "start_point": form.start_point,
    }


@per_repository_router.delete(
    "/branches/{branch_name:path}",
    summary="Delete a branch from a repository",
    response_model=RepositoryBranchDeleteResponseModel,
)
async def delete_branch(
    repo: Annotated[Repository, Depends(acquire_repository)],
    branch_name: Annotated[
        str, FastAPIPath(..., description="The name of the branch to delete")
    ],
):
    """Endpoint to delete a branch in a specific repository."""
    # Placeholder implementation
    await repo.git_service.branches.delete(repo.repo_path, branch_name)
    return {"message": f"Branch '{branch_name}' deleted successfully"}


repositories_router.include_router(per_repository_router)
