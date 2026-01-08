import json
import starlette
import starlette.applications
import starlette.requests
import starlette.responses
from starlette.routing import Route


async def rpc_handler(request: starlette.requests.Request) -> starlette.responses.Response:
    b = await request.body()
    print(b)
    print(json.loads(b))
    return starlette.responses.JSONResponse({"message": "RPC endpoint"})


routes = [
    Route("/rpc", endpoint=rpc_handler, methods=["POST"]),
]

app = starlette.applications.Starlette(routes=routes)
