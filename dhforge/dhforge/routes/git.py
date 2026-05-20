from typing import Annotated

from dhforge.logger import get_logger
from dhforge.services.deps import acquire_git_service
from dhforge.services.git import GitService
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

git_router = APIRouter(prefix="/git", tags=["git"])
logger = get_logger()


class GitVersionResponseModel(BaseModel):
    version: str = Field(
        ..., description="The version of the git binary", examples=["2.30.0"]
    )


@git_router.get(
    "/version",
    response_model=GitVersionResponseModel,
    summary="Get git version",
)
async def git_version(git_service: Annotated[GitService, Depends(acquire_git_service)]):
    """Endpoint to retrieve the version of the git binary installed on the system."""

    version = await git_service.version()
    return {"version": version}
