from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from shared import ContentTypeMiddleware, templates

APPS = {
    "/wikidata": "wikidata:app",
    "/cgi": "cgilike:app",
}


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

for prefix, app_path in APPS.items():
    module_name, app_name = app_path.split(":")
    module = __import__(module_name)
    app.mount(prefix, getattr(module, app_name))
