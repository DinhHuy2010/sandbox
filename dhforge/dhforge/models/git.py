from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, computed_field


class Author(BaseModel):
    name: str = Field(
        ..., description="The name of the commit author", examples=["John Doe"]
    )
    email: EmailStr = Field(
        ...,
        description="The email of the commit author",
        examples=["john.doe@example.com"],
    )


class Commit(BaseModel):
    hash: str = Field(
        ...,
        description="The commit hash",
        examples=["7f3a9c2b8e4d6f1a0c9b5d3e2f8a6b4c1d0e9f7a"],
    )
    author: Author = Field(..., description="The author of the commit")
    date: datetime = Field(
        ..., description="The date of the commit", examples=["2023-01-01T12:00:00Z"]
    )
    message: str = Field(
        ..., description="The commit message", examples=["Initial commit"]
    )


class Reference(BaseModel):
    name: str = Field(
        ..., description="The name of the reference", examples=["refs/heads/main"]
    )
    object_hash: str = Field(
        ...,
        description="The commit hash that the reference points to",
        examples=["7f3a9c2b8e4d6f1a0c9b5d3e2f8a6b4c1d0e9f7a"],
    )

    @computed_field
    @property
    def is_branch(self) -> bool:
        return self.name.startswith("refs/heads/")

    @computed_field
    @property
    def is_tag(self) -> bool:
        return self.name.startswith("refs/tags/")

    @property
    def branch_name(self) -> str:
        if self.is_branch:
            return self.name[len("refs/heads/") :]
        raise ValueError("Reference is not a branch")

    @property
    def tag_name(self) -> str:
        if self.is_tag:
            return self.name[len("refs/tags/") :]
        raise ValueError("Reference is not a tag")
