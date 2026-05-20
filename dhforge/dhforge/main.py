import traceback

import content_negotiation
import fastapi
from fastapi.responses import PlainTextResponse, RedirectResponse
from dhforge.logger import get_logger
from dhforge.routes.health import health_router
from dhforge.routes.git import git_router
from dhforge.routes.repositories import repositories_router
from dhforge.services.exceptions import DHFServiceException

app = fastapi.FastAPI(
    openapi_tags=[
        {
            "name": "health",
            "description": "Endpoints related to health checks and status monitoring.",
        },
        {
            "name": "git",
            "description": "Endpoints related to git operations and information.",
        },
        {
            "name": "repositories",
            "description": "Endpoints for managing git repositories.",
        },
    ],
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        }
    ],
)
logger = get_logger()
logger.instrument_fastapi(app, capture_headers=True)


@app.get("/", include_in_schema=False)
async def root(request: fastapi.Request):
    content_type = content_negotiation.decide_content_type(
        request.headers.getlist("accept"),
        ["application/json", "text/html"],
    )
    match content_type:
        case "application/json":
            return {"message": "Hello, World!", "docs": app.docs_url}
        case "text/html":
            return RedirectResponse(url=app.docs_url)  # type: ignore
        case _:
            raise fastapi.HTTPException(status_code=406)


message = """
An error occurred while processing your request. Please try again later.
Error code: {error_code}
Message: {message}
"""
message_with_traceback = """
An error occurred while processing your request. Please try again later.
Error code: {error_code}
Message: {message}

=== Traceback (for debugging purposes) ===
{traceback}
"""


@app.exception_handler(DHFServiceException)
async def dhf_service_exception_handler(
    request: fastapi.Request, exc: DHFServiceException
) -> fastapi.Response:
    logger.error(f"Service exception occurred: {exc}", _exc_info=exc)
    traceback_str = "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
    return PlainTextResponse(
        status_code=500,
        content=message_with_traceback.format(
            error_code=exc.error_code,
            message=str(exc),
            traceback=traceback_str,
        ),
    )


api_router = fastapi.APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(git_router)
api_router.include_router(repositories_router)
app.include_router(api_router)
