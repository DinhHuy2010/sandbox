from typing import Any, Callable, Mapping

from content_negotiation import NoAgreeableContentTypeError, decide_content_type
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route
from starlette.templating import Jinja2Templates
from starlette.types import ASGIApp

templates = Jinja2Templates(directory="templates")


class ContentTypeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, mapping: Mapping[str, Callable[..., Any]]) -> None:
        self.mapping = mapping
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        types = request.headers.getlist("Accept")
        try:
            content_type = decide_content_type(types, list(self.mapping.keys()))
            request.state.content_type = content_type
            handler = self.mapping[content_type]
            response = await handler(request)
            return response
        except NoAgreeableContentTypeError:
            return await call_next(request)


async def home(request: Request) -> Response:
    return PlainTextResponse("Hello, world!")


async def hello_world_in_html(request: Request) -> Response:
    return templates.TemplateResponse(
        "hello.html",
        {"request": request, "message": "Hello, world in HTML!"},
    )


async def hello_world_in_plain_text(request: Request) -> Response:
    return PlainTextResponse("Hello, world in plain text!")


async def hello_world_in_xml(request: Request) -> Response:
    return Response(
        content="<?xml version='1.0' encoding='UTF-8'?><message>Hello, world in XML!</message>",
        media_type="application/xml",
    )


async def hello_world_in_json(request: Request) -> Response:
    return JSONResponse({"message": "Hello, world in JSON!"})


async def home_with_content_negotiation_fallback(request: Request) -> Response:
    content_type = getattr(request.state, "content_type", None)
    if content_type is None:
        return Response("Not Acceptable", status_code=406)
    return Response(f"Not Acceptable: {content_type}", status_code=406)


app = Starlette(
    routes=[
        Route("/", home),
        Route(
            "/content-negotiation",
            home_with_content_negotiation_fallback,
            middleware=[
                Middleware(
                    ContentTypeMiddleware,
                    mapping={
                        "text/html": hello_world_in_html,
                        "text/plain": hello_world_in_plain_text,
                        "application/xml": hello_world_in_xml,
                        "application/json": hello_world_in_json,
                    },
                )
            ],
        ),
    ],
)
