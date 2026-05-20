from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class DHFServiceException(Exception):
    """Base exception for all service-related errors."""

    error_code: str = Field(
        ..., description="A unique error code for this exception type"
    )

    def message(self) -> str:
        """Return a user-friendly error message."""
        raise NotImplementedError("Subclasses must implement the message method")

    def __str__(self):
        try:
            return self.message()
        except NotImplementedError:
            return f"{self.__class__.__name__} occurred without"


@dataclass
class DHFGitCommandError(DHFServiceException):
    error_code: str = Field(
        "git-command-error",
        description="A unique error code for this exception type",
        init=False,
    )
    binary_location: str = Field(..., description="The location of the git binary")
    command_args: list[str] = Field(..., description="The git command that failed")
    stderr: str = Field(..., description="The error output from the git command")
    exit_code: int = Field(..., description="The exit code returned by the git command")
    pid: int = Field(..., description="The process ID of the git command")

    def message(self) -> str:
        return (
            f"Git command failed with exit code {self.exit_code} (PID {self.pid}): "
            f"{' '.join(self.command_args)}\nError output: {self.stderr}"
        )


@dataclass
class DHFRepositoryNotFoundError(DHFServiceException):
    error_code: str = Field(
        "repository-not-found",
        description="A unique error code for this exception type",
        init=False,
    )
    name: str

    def __str__(self):
        return f"Repository '{self.name}' not found"


@dataclass
class DHFRepositoryAlreadyExistsError(DHFServiceException):
    error_code: str = Field(
        "repository-already-exists",
        description="A unique error code for this exception type",
        init=False,
    )
    name: str

    def __str__(self):
        return f"Repository '{self.name}' already exists"
