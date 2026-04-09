# from dataclasses import dataclass
# from typing import Iterable

from datetime import datetime
from typing import Any

from packaging.utils import parse_wheel_filename
import pydantic_core
from httpx import Client
from packaging.version import VERSION_PATTERN, Version
from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    GetCoreSchemaHandler,
    HttpUrl,
    computed_field,
    model_validator,
)
from pydantic.dataclasses import dataclass
from pydantic_core import CoreSchema


class PackagingVersion(Version):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return pydantic_core.core_schema.str_schema(pattern=f"^{VERSION_PATTERN}$")


class RegistryInfo(BaseModel):
    name: str
    base_url: str

    def project(self, name: str) -> str:
        return f"{self.base_url}{name}/"


# -------------------------
# Meta
# -------------------------


class Meta(BaseModel):
    model_config = {"extra": "ignore"}
    api_version: str = Field(alias="api-version")


# -------------------------
# Project (index page)
# -------------------------


class Project(BaseModel):
    name: str


class IndexResponse(BaseModel):
    meta: Meta
    projects: list[Project]


# -------------------------
# File hashes
# -------------------------


class Hashes(BaseModel):
    model_config = {"extra": "forbid"}
    sha256: str | None = None


# -------------------------
# Distribution file
# -------------------------


class File(BaseModel):
    model_config = {"extra": "allow"}
    filename: str
    url: HttpUrl
    size: int

    hashes: Hashes | None = None
    requires_python: str | None = Field(default=None, alias="requires-python")
    yanked: str | bool | None = Field(default=None)
    provenance: HttpUrl | None = None

    # PEP 700
    upload_time: datetime | None = Field(default=None, alias="upload-time")

    # PEP 658, 714

    core_metadata: bool | Hashes | None = Field(
        default=None,
        alias="core-metadata",
        validation_alias=AliasChoices(
            "core-metadata",
            "data-dist-info-metadata",
            "dist-info-metadata",
        ),
    )

    @model_validator(mode="before")
    def handle_core_metadata_field(cls, data: dict[str, Any]) -> dict[str, Any]:
        if "core-metadata" in data:
            data.pop("data-dist-info-metadata", None)
            data.pop("dist-info-metadata", None)
            return data
        for alias in ("data-dist-info-metadata", "dist-info-metadata"):
            if alias in data:
                data["core-metadata"] = data[alias]
                data.pop(alias, None)
        return data

    @property
    def package_type(self) -> str:
        if self.filename.endswith(".whl"):
            return "wheel"
        elif self.filename.endswith((".tar.gz", ".zip")):
            return "sdist"
        else:
            return "unknown"

    @property
    def name(self) -> str:
        if self.package_type == "wheel":
            return parse_wheel_filename(self.filename)[0]
        elif self.package_type == "sdist":
            return self.filename.rsplit("-", 1)[0]
        else:
            raise ValueError(
                f"Cannot determine package name from filename: {self.filename}"
            )

    # @property
    # def version(self) -> PackagingVersion:
    #     if self.package_type == "wheel":
    #         return PackagingVersion(str(parse_wheel_filename(self.filename)[1]))
    #     elif self.package_type == "sdist":
    #         version_str = PackagingVersion
    #         return PackagingVersion(version_str)
    #     else:
    #         raise ValueError(
    #             f"Cannot determine package version from filename: {self.filename}"
    #         )


# -------------------------
# Project response
# -------------------------


class ProjectStatus(BaseModel):
    status: str


class ProjectResponse(BaseModel):
    model_config = {"extra": "allow"}
    project_status: ProjectStatus = Field(alias="project-status")
    alternate_locations: list[HttpUrl] = Field(alias="alternate-locations")
    meta: Meta
    name: str
    files: list[File]
    versions: list[PackagingVersion]


@dataclass
class SimpleClient:
    base_url = "https://pypi.org/simple/"


registry = RegistryInfo(name="pypi", base_url="https://pypi.org/simple/")

client = Client(
    follow_redirects=True, headers={"Accept": "application/vnd.pypi.simple.v1+json"}
)
o = client.get(registry.project("requests")).json()
print(ProjectResponse.model_json_schema())
