from os import scandir
from pathlib import Path
from typing import Annotated

import magika
from fastapi import Depends, FastAPI, Query, Request
from fastapi import Path as FastAPIPath
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

BASE_DIR = (
    Path.cwd().resolve()
)  # Set the base directory to the current working directory


app = FastAPI()
m = magika.Magika()


def resolve_path(path: str) -> Path:
    """
    Resolves a relative path to an absolute path based on the BASE_DIR.
    Handle directory traversal attempts by normalizing the path.
    """
    # Create a Path object from the relative path
    relative_path_obj = Path(path)

    # Normalize the path to prevent directory traversal
    normalized_path = (BASE_DIR / relative_path_obj).resolve()

    # Ensure the resolved path is within the BASE_DIR
    # if not str(normalized_path).startswith(str(BASE_DIR)):
    if not normalized_path.is_relative_to(BASE_DIR):
        raise HTTPException(
            status_code=403, detail="Attempted directory traversal detected!"
        )

    return normalized_path


def resolve_path_dependency(path: Annotated[str, FastAPIPath()]) -> Path:
    return resolve_path(path)


def detect_file_type(file_path: Path) -> magika.MagikaResult:
    """
    Detects the file type using the magika library.
    """
    try:
        file_type = m.identify_path(str(file_path))
        return file_type
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting file type: {e}")


@app.api_route(
    "/serve/{path:path}", response_class=FileResponse, methods=["GET", "HEAD"]
)
def serve_file(file_path: Annotated[Path, Depends(resolve_path_dependency)]):
    """
    Endpoint to serve a file from the BASE_DIR.
    """
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    ft = detect_file_type(file_path)
    ift = ft.output.mime_type

    return FileResponse(path=file_path, media_type=ift, filename=file_path.name)

    # return {"file_path": str(file_path)}


def out_path(path: Path) -> str:
    """
    Returns the relative path of the given path with respect to BASE_DIR.
    """
    o = str(path.relative_to(BASE_DIR))
    if o == ".":
        return "/"
    return "/" + o


@app.get("/listing")
def list_directory(resource: Annotated[str, Query()] = ""):
    """
    Endpoint to list the contents of a directory.
    """
    path = resolve_path(
        resource.lstrip("/")
    )  # Remove leading slash for relative path resolution

    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    # List the contents of the directory
    # contents = [item.name for item in path.iterdir()]
    with scandir(path) as it:
        return {
            "directory": out_path(path),
            "contents": [
                {
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "is_file": item.is_file(),
                    "size": item.stat().st_size,
                    "last_modified": item.stat().st_mtime,
                }
                for item in it
            ],
        }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom exception handler for HTTPException to return JSON responses.
    """
    return PlainTextResponse(exc.detail, status_code=exc.status_code)
