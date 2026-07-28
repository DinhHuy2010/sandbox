from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import traceback
from typing import Any
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

app = Starlette()
BASE_DIR = "cgi-bin"


def get_script(fn: str) -> Path:
    return Path(BASE_DIR) / fn


def execute_cgi(request: Request, content: str):
    headers: dict[str, str] = {}
    status = 200
    media_type = "text/plain"
    output = StringIO()

    def set_header(key: str, value: str):
        headers[key.lower()] = value

    def set_status(code: int):
        nonlocal status
        status = code

    def set_media_type(mt: str):
        nonlocal media_type
        media_type = mt

    def get_state() -> Any:
        return {
            "request": request,
            "method": request.method,
            "headers": request.headers,
            "path_params": request.path_params,
            "query_params": request.query_params,
        }

    def get_params() -> dict[str, Any]:
        return dict(request.query_params)

    ns: dict[str, Any] = {}
    ns["get_state"] = get_state
    ns["set_header"] = set_header
    ns["set_status"] = set_status
    ns["get_params"] = get_params
    ns["set_media_type"] = set_media_type

    with redirect_stdout(output):
        try:
            exec(content, ns)
        except SystemExit as e:
            if e.code is not None and e.code != 0:
                print(f"CGI script exited with code {e.code!r}.")
        except BaseException as e:
            media_type = "text/plain"
            print("=====================================")
            print("Error executing CGI script:\n")
            traceback.print_exception(type(e), e, e.__traceback__, file=output)
    return Response(
        content=output.getvalue(),
        headers=headers,
        status_code=status,
        media_type=media_type,
    )


def cgi_handler(request: Request) -> Response:
    filename = request.path_params["filename"]
    script_path = get_script(filename)
    try:
        with script_path.open("r") as f:
            script_content = f.read()
    except FileNotFoundError:
        return Response("CGI script not found", status_code=404)
    # Here you would normally execute the CGI script and capture its output.
    # For simplicity, we'll just return the script path.
    return execute_cgi(request, script_content)


app.add_route("/{filename}", cgi_handler)
