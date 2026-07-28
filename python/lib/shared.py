from typing import Any, Callable, Mapping

from content_negotiation import NoAgreeableContentTypeError, decide_content_type
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
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
        types = request.headers.get("Accept", "").split(",")
        request.state.accept = types
        try:
            content_type = decide_content_type(types, list(self.mapping.keys()))
            handler = self.mapping[content_type]
            response = await handler(request)
            return response
        except NoAgreeableContentTypeError:
            return await call_next(request)
