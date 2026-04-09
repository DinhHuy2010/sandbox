from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings

from graphql_caller import caller


class Settings(BaseSettings):
    github_token: str
    debug_secret: str
    include_github_data: bool = True


def get_settings() -> Settings:
    return Settings(_env_file=".env")


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def mandate_internal_secret(
    settings: SettingsDependency, x_debug_secret: Annotated[str, Header()]
):
    if x_debug_secret != settings.debug_secret:
        raise HTTPException(status_code=403, detail="Forbidden")


internal = APIRouter(
    prefix="/_internal",
    include_in_schema=False,
    dependencies=[Depends(mandate_internal_secret)],
)
main = APIRouter()
templates = Jinja2Templates(directory="templates")


def to_beautiful_datetime(datetime_str: str) -> str:
    from datetime import datetime

    dt = datetime.fromisoformat(datetime_str)
    # like "4 July 1776 at HH:MM:SS"
    return dt.strftime("%-d %B %Y at %H:%M:%S")


templates.env.filters["to_beautiful_datetime"] = to_beautiful_datetime


@internal.get("/settings")
def info(settings: SettingsDependency) -> Settings:
    return settings


@main.get("/health")
def health() -> Any:
    return {"status": "ok"}


@main.get("/")
def root() -> Any:
    return {"message": "Hello, World!", "docs": "/docs"}


@main.get("/data/{repo_owner}/{repo_name}", response_class=HTMLResponse)
def data(_: Request, settings: SettingsDependency, repo_owner: str, repo_name: str) -> HTMLResponse:
    data = caller(settings, repo_owner, repo_name)
    return templates.TemplateResponse(
        "stars.html",
        {
            "request": _,
            "data": data,
            "include_github_data": settings.include_github_data,
        },
    )


app = FastAPI()
app.include_router(internal)
app.include_router(main)
