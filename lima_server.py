from okwhatever3 import imports, asyncize

imports.uvicorn.run(
    imports["starlette.applications"].Starlette(
        routes=[
            imports.starlette.routing.Route(
                "/",
                asyncize(
                    lambda request: imports.starlette.responses.PlainTextResponse(
                        "Hello, world!"
                    )
                ),
            ),
            imports.starlette.routing.Route(
                "/items/{item_id}",
                asyncize(
                    lambda request: imports.starlette.responses.PlainTextResponse(
                        f"Item ID: {request.path_params['item_id']} ({request.client.host}:{request.client.port})"
                    )
                ),
            ),
        ]
    ),
    host="127.0.0.1",
    port=8000,
)
