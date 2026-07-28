import starlette.applications
import starlette.requests
import starlette.responses
import starlette.routing


def hello(request: starlette.requests.Request) -> starlette.responses.Response:
    return starlette.responses.PlainTextResponse("Hello, world!")


app = starlette.applications.Starlette(
    routes=[
        starlette.routing.Route("/", hello),
    ]
)
