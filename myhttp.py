# pyright: strict, reportFunctionMemberAccess=false, reportMissingTypeStubs=false

"""Super micro HTTP framework for Python."""

from dataclasses import dataclass
from inspect import getmembers
from types import ModuleType
from typing import Any, Callable, NotRequired, Protocol, Sequence, TypedDict
from wsgiref.types import WSGIApplication

from werkzeug import Request, Response
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule


type NextMiddleware = Callable[[RequestContext], Response]
type Middleware = Callable[[RequestContext, NextMiddleware], Response]
type EndpointCallable = Callable[[RequestContext], Response]


@dataclass
class RequestContext:
    request: Request
    values: dict[str, Any]


class EndpointInfo(TypedDict):
    route: str | None
    methods: NotRequired[list[str]]
    middlewares: NotRequired[list[Middleware]]


class EndpointFunction(Protocol):
    __endpoint__: EndpointInfo

    def __call__(self, context: RequestContext) -> Response: ...


def apply_middleware(
    handler: EndpointCallable, middleware: Middleware
) -> EndpointCallable:
    def wrapped(context: RequestContext) -> Response:
        return middleware(context, handler)

    return wrapped


def apply_middlewares(
    handler: EndpointCallable, middlewares: Sequence[Middleware]
) -> EndpointCallable:
    for middleware in reversed(middlewares):
        handler = apply_middleware(handler, middleware)
    return handler


def _init_endpoint(func: EndpointCallable) -> EndpointFunction:
    func.__endpoint__ = {"route": None}
    return func  # pyright: ignore[reportReturnType]


def middleware(
    *middlewares: Middleware,
) -> Callable[[EndpointFunction | EndpointCallable], EndpointFunction]:
    def decorator(func: EndpointFunction | EndpointCallable) -> EndpointFunction:
        if not hasattr(func, "__endpoint__"):
            func = _init_endpoint(func)
        endpoint_info = func.__endpoint__
        if "middlewares" not in endpoint_info:
            endpoint_info["middlewares"] = []
        endpoint_info["middlewares"] = list(middlewares) + endpoint_info["middlewares"]
        func.__endpoint__ = endpoint_info
        return func  # pyright: ignore[reportReturnType]

    return decorator


def endpoint(
    route: str, methods: list[str] | None = None
) -> Callable[[EndpointCallable], EndpointFunction]:
    def decorator(func: EndpointCallable) -> EndpointFunction:
        if not hasattr(func, "__endpoint__"):
            func = _init_endpoint(func)
        func.__endpoint__["route"] = route
        if methods is not None:
            func.__endpoint__["methods"] = methods
        return func  # type: ignore

    return decorator


def _name_or_repr(obj: Any) -> str:
    try:
        return obj.__name__
    except AttributeError:
        return repr(obj)


def create_rules(functions: list[EndpointFunction]) -> Map:
    rules: list[Rule] = []
    for func in functions:
        endpoint_info: EndpointInfo | None = getattr(func, "__endpoint__", None)
        if endpoint_info is None:
            continue
        if endpoint_info["route"] is None:
            raise ValueError(
                f"Endpoint function {_name_or_repr(func)} has no route defined."
            )
        wrapped_func = apply_middlewares(func, endpoint_info.get("middlewares", []))
        rules.append(
            Rule(
                endpoint_info["route"],
                methods=endpoint_info.get("methods"),
                endpoint=wrapped_func,
            )
        )
    return Map(rules)


def execute_endpoint(func: EndpointFunction, context: RequestContext) -> Response:
    return func(context)


def create_main_handler(
    rules: Map, middlewares: list[Middleware]
) -> Callable[[RequestContext], Response]:
    def main_handler(context: RequestContext) -> Response:
        adapter = rules.bind_to_environ(context.request.environ)
        try:
            endpoint, values = adapter.match()
            values = dict(values)
            return execute_endpoint(
                endpoint, RequestContext(request=context.request, values=values)
            )
        except HTTPException as e:
            return e.get_response(context.request)

    return apply_middlewares(main_handler, middlewares)


@dataclass
class Server:
    handlers: list[EndpointFunction]
    middlewares: list[Middleware]


def collect_server_from_module(obj: ModuleType) -> Server:
    handlers: list[EndpointFunction] = []
    middlewares: list[Middleware] = []
    middlewares.extend(getattr(obj, "__middlewares__", []))
    if hasattr(obj, "__handlers__"):
        handlers = getattr(obj, "__handlers__", [])
    else:
        for _, member in getmembers(obj):
            if callable(member) and hasattr(member, "__endpoint__"):
                handlers.append(member)  # type: ignore
    for handler in handlers:
        if not hasattr(handler, "__endpoint__"):
            raise ValueError(f"Handler {_name_or_repr(handler)} is not an endpoint.")
    return Server(handlers=handlers, middlewares=middlewares)


def create_server(
    source: list[EndpointFunction] | ModuleType | Server,
) -> WSGIApplication:
    if isinstance(source, ModuleType):
        server = collect_server_from_module(source)
    elif isinstance(source, Server):
        server = source
    else:
        server = Server(handlers=source, middlewares=[])

    rules = create_rules(server.handlers)
    main_handler = create_main_handler(rules, server.middlewares)

    @Request.application
    def wsgi_app(request: Request) -> Response:
        return main_handler(RequestContext(request=request, values={}))

    return wsgi_app


@endpoint("/", methods=["GET"])
def handler(context: RequestContext) -> Response:
    return Response("Hello, World!")


@endpoint("/hello/<name>", methods=["GET"])
def hello(context: RequestContext) -> Response:
    return Response(f"Hello, {context.values['name']}!")


def test_middleware(name: str) -> Middleware:
    def middleware(context: RequestContext, next: NextMiddleware) -> Response:
        print(f"{name} middleware before")
        response = next(context)
        print(f"{name} middleware after")
        return response

    return middleware


@endpoint("/middleware", methods=["GET"])
@middleware(test_middleware("First"), test_middleware("Second"))
@middleware(test_middleware("Third"))
@middleware(test_middleware("Fourth"))
def middleware_handler(context: RequestContext) -> Response:
    return Response("This is the main handler.")


if __name__ == "__main__":
    from werkzeug.serving import run_simple
    import myhttp_example

    run_simple("localhost", 4000, create_server(myhttp_example))
