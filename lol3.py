from http import HTTPStatus

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Route

from build_gibbrish_openapi import build_gibberish_openapi

lolmao = build_gibberish_openapi()


def get_random_openapi(request: Request) -> Response:
    return JSONResponse(lolmao.model_dump(exclude_none=True, by_alias=True))


def swagger(request: Request) -> Response:
    return FileResponse("./swagger.html", media_type="text/html")


def refresh(request: Request) -> Response:
    global lolmao
    lolmao = build_gibberish_openapi()
    return Response(status_code=HTTPStatus.NO_CONTENT)


app = Starlette(
    routes=[
        Route("/openapi.json", get_random_openapi),
        Route("/", swagger),
        Route("/refresh", refresh),
    ]
)
