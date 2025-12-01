from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware import Middleware

from shared import ContentTypeMiddleware, templates


async def homepage(request: Request) -> Response:
    return Response("Hello, World!")


# /external/<property>/<ID>
async def external_id_html(request: Request) -> Response:
    wd_property = request.path_params["property"]
    id = request.path_params["id"]
    return templates.TemplateResponse(
        "wd_external_id.html",
        {"request": request, "property": wd_property, "id": id},
    )


async def fallback(request: Request) -> Response:
    accept = getattr(request.state, "accept", None)
    if accept is None:
        return Response("Not Acceptable", status_code=406)
    return Response(f"Not Acceptable: {accept}", status_code=406)

app = Starlette()
app.routes.append(Route("/", homepage))
app.routes.append(
    Route(
        "/external/{property}/{id}",
        fallback,
        middleware=[
            Middleware(
                ContentTypeMiddleware,
                mapping={
                    "text/html": external_id_html,
                },
            )
        ],
    )
)
