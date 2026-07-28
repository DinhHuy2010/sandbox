# pyright: standard

from __future__ import annotations

from typing import Annotated, Callable, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, Discriminator, Field, JsonValue
from pydantic.dataclasses import dataclass


class BaseEnvelope(BaseModel):
    envelope: Literal["1.0"] = Field(default="1.0", init=False)

    def bind[_EnvT: BaseEnvelope](self, func: Callable[[Self], _EnvT]) -> _EnvT:
        return func(self)


class Request(BaseEnvelope):
    type: Literal["request"] = Field(default="request", init=False)
    id: str
    name: str
    params: dict[str, JsonValue]
    state: dict[str, JsonValue] = Field(default_factory=dict)


class OKResponse(BaseEnvelope):
    type: Literal["response"] = Field(default="response", init=False)
    status: Literal["ok"] = Field(default="ok", init=False)
    id: str
    name: str
    result: dict[str, JsonValue]
    state: dict[str, JsonValue] = Field(default_factory=dict)
    context: dict[str, JsonValue] = Field(default_factory=dict)


class ErrorResponse(BaseEnvelope):
    type: Literal["response"] = Field(default="response", init=False)
    status: Literal["error"] = Field(default="error", init=False)
    id: str
    name: str
    error: dict[str, JsonValue]
    context: dict[str, JsonValue] = Field(default_factory=dict)


@dataclass
class Router:
    handlers: dict[str, EndpointHandler] = Field(default_factory=dict, init=False)

    def route(self, request: Request) -> Response | Router:
        handler = self.handlers.get(request.name)
        if handler is None:
            return ErrorResponse(
                id=request.id,
                name=request.name,
                error={"message": f"Unknown endpoint: {request.name}"},
            )
        return handler(request)

    def register(self, name: str) -> Callable[[EndpointHandler], EndpointHandler]:
        def decorator(func: EndpointHandler) -> EndpointHandler:
            self.handlers[name] = func
            return func

        return decorator


@dataclass
class Client:
    router: Router

    def create_request(self, name: str, params: dict[str, JsonValue]) -> Request:
        return Request(id=str(uuid4()), name=name, params=params)

    def send_request(self, request: Request) -> Response | Router:
        return self.router.route(request)

    def call(self, name: str, /, **params: JsonValue) -> Response | Router:
        request = self.create_request(name, params)
        return self.send_request(request)

    @property
    def fluent(self) -> FluentClient:
        return FluentClient(self)


@dataclass
class FluentClient:
    _client: Client = Field(alias="client", repr=False)

    def __getattr__(self, name: str) -> Callable[..., Response | FluentClient]:
        def method(**params: JsonValue) -> Response | FluentClient:
            result = self._client.call(name, **params)
            if isinstance(result, Router):
                return FluentClient(Client(result))
            return result

        return method


Response = Annotated[OKResponse | ErrorResponse, Discriminator("status")]
StandardEnvelope = Annotated[Request | Response, Discriminator("type")]
EndpointHandler = Callable[[Request], Response | Router]
EnvelopeProcessor = Callable[[StandardEnvelope], StandardEnvelope]

router = Router()


@router.register("echo")
def echo_handler(request: Request) -> OKResponse:
    return OKResponse(
        id=request.id,
        name=request.name,
        result={"echo": request.params},
    )


@router.register("div")
def div_handler(request: Request) -> Response:
    try:
        a = request.params["a"]
        b = request.params["b"]
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise ValueError("Parameters 'a' and 'b' must be numbers.")
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        result = a / b
        return OKResponse(
            id=request.id,
            name=request.name,
            result={"result": result},
        )
    except Exception as e:
        return ErrorResponse(
            id=request.id,
            name=request.name,
            error={"message": str(e)},
        )


@router.register("private")
def private_handler(request: Request) -> Router:
    router = Router()

    @router.register("secret")
    def secret_handler(request: Request) -> OKResponse:
        return OKResponse(
            id=request.id,
            name=request.name,
            result={"message": "This is a secret endpoint."},
        )

    return router


client = Client(router)
p = client.fluent
r = p.private().secret()
print(r.result)
