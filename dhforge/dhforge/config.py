from pathlib import Path
import tomllib

from pydantic import BaseModel, Field


class RepositoriesConfig(BaseModel):
    index_file: Path = Field(
        ...,
        description="Path to the JSON file that contains the repository index",
        alias="index-file",
    )
    repositories_base_dir: Path = Field(
        ...,
        description="Path to the base directory for repositories",
        alias="repositories-base-dir",
    )


class Config(BaseModel):
    repositories: RepositoriesConfig


def read_config(config_path: Path | None = None) -> Config:
    if config_path is None:
        config_path = Path("config.toml")
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration file '{config_path}' not found")
    with config_path.open("rb") as f:
        t = tomllib.load(f)
    return Config.model_validate(t)
