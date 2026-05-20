# pyright: standard, reportFunctionMemberAccess=false

# Middleware chain:
# Server ->
# [(parent Router class middlewares) -> (parent Router instance middlewares) ->]
# ...
# (Router class middlewares) -> (Router instance middlewares) -> Route handler

from __future__ import annotations

import pkgutil
from dataclasses import dataclass, field
from inspect import isfunction
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Concatenate,
    Protocol,
    Sequence,
    cast,
    overload,
    runtime_checkable,
)

from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response

_F = Callable[..., Response]
type RouterSelfRouteCallable = Callable[Concatenate[Router, Request, ...], Response]
type RouterBoundRouteCallable = Callable[Concatenate[Request, ...], Response]
type Route = RouterSelfRouteCallable | Router
type NextMiddleware = Callable[[MiddlewareContext], Response]
type Middleware = Callable[[MiddlewareContext, NextMiddleware], Response]

FinalHandler = NextMiddleware


def special_path(path: str) -> Callable[[_F], _F]:
    def decorator(func: _F) -> _F:
        if hasattr(func, "__not_a_route__"):
            raise ValueError(
                f"Function {func.__name__} is marked as not a route, cannot assign special path {path!r}"
            )
        if hasattr(func, "__special_path__"):
            raise ValueError(
                f"Function {func.__name__} already has a special path: {func.__special_path__!r}"
            )

        func.__special_path__ = path
        return func

    return decorator


def not_a_route(func: _F) -> _F:
    func.__not_a_route__ = True
    return func


def force_as_route(func: _F) -> _F:
    if hasattr(func, "__not_a_route__") and func.__not_a_route__:
        raise ValueError(
            f"Function {func.__name__} is marked as not a route, cannot be used as a route"
        )
    func.__is_a_route__ = True
    return func


def is_route(name: str, func: Callable[..., Any]) -> bool:
    if not isfunction(func):
        return False
    if name.startswith("_") and not getattr(func, "__is_a_route__", False):
        return False
    return not getattr(func, "__not_a_route__", False)


def create_url_map(namespace: dict[str, Any]) -> dict[str, Route]:
    routes = {}
    for name, value in namespace.items():
        if is_route(name, value):
            if hasattr(value, "__special_path__"):
                path = value.__special_path__
            else:
                path = name
            routes[path] = value
        elif isinstance(value, Router):
            routes[name] = value
    root_point_to = namespace.get("__root_point_to__")
    if root_point_to:
        if root_point_to not in routes:
            raise ValueError(
                f"__root_point_to__ is set to {root_point_to!r} but no such route exists"
            )
        routes[""] = routes[root_point_to]
    special_path_routes = namespace.get("__special_path_routes__", {})
    for path, handler_name in special_path_routes.items():
        if handler_name not in namespace:
            raise ValueError(
                f"Special path {path!r} points to {handler_name!r} but no such handler exists"
            )
        handler = namespace[handler_name]
        if not is_route(handler_name, handler):
            raise ValueError(
                f"Handler {handler_name!r} for special path {path!r} is not a valid route"
            )
        routes[path] = handler

    return routes


def collect_dependencies(
    namespace: dict[str, Any],
) -> dict[str, DependencyProtocol[Any]]:
    dependencies = {}
    for name, value in namespace.items():
        if isinstance(value, DependencyProtocol):
            dependencies[name] = value
    extra = namespace.get("__dependencies__", {})
    dependencies.update(extra)
    return dependencies


def route_middlewares(middlewars: Middleware | list[Middleware]) -> Callable[[_F], _F]:
    if not isinstance(middlewars, list):
        middlewars = [middlewars]

    def decorator(func: _F) -> _F:
        if hasattr(func, "__not_a_route__"):
            raise ValueError(
                f"Function {func.__name__} is marked as not a route, cannot assign middlewares"
            )
        if hasattr(func, "__route_middlewares__"):
            # raise ValueError(
            #     f"Function {func.__name__} already has route middlewares: {func.__route_middlewares__!r}"
            # )
            func.__route_middlewares__.extend(middlewars)  # type: ignore
        else:
            func.__route_middlewares__ = middlewars
        return func

    return decorator


def _wrap_middlewares(
    handler: RouterBoundRouteCallable,
    middlewares: Sequence[Middleware],
) -> FinalHandler:
    def make_next(mw: Middleware, next_handler: NextMiddleware) -> FinalHandler:
        def wrapped(ctx: MiddlewareContext) -> Response:
            return mw(ctx, next_handler)

        return wrapped

    def final_handler(ctx: MiddlewareContext) -> Response:
        return handler(ctx.request, **ctx.values)

    for mw in reversed(middlewares):
        final_handler = make_next(mw, final_handler)  # type: ignore
    return final_handler


@runtime_checkable
class DependencyProtocol[D](Protocol):
    def resolve(self) -> D: ...

    @overload
    def __get__(self, instance: None, owner: type) -> DependencyProtocol[D]: ...
    @overload
    def __get__(self, instance: Any, owner: type) -> D: ...
    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        return self.resolve()


class Dependency[**P, T](DependencyProtocol[T]):
    def __init__(
        self,
        resolver: Callable[..., T] | DependencyProtocol[Callable[..., T]],
        *rargs: P.args,
        **rkwargs: P.kwargs,
    ):
        self.resolver = resolver
        self.rargs = rargs
        self.rkwargs = rkwargs

    def resolve(self) -> T:
        if isinstance(self.resolver, DependencyProtocol):
            resolver = self.resolver.resolve()
            if not callable(resolver):
                raise ValueError(f"Resolved dependency {resolver!r} is not callable")
            # self.resolver = resolver
        else:
            resolver = self.resolver
        return resolver(*self.rargs, **self.rkwargs)  # type: ignore


class ExternalDependency[E](DependencyProtocol[E]):
    __sentinel__ = object()

    def __init__(self, name: str):
        self.name = name
        self._obj: E | object = self.__sentinel__

    def resolve(self) -> E:
        if self._obj is self.__sentinel__:
            self._obj = pkgutil.resolve_name(self.name)
        return self._obj  # type: ignore


class InheritableDependency[W](DependencyProtocol[W]):
    def __init__(self, wrapped_dependency: DependencyProtocol[W]):
        self.wrapped_dependency = wrapped_dependency

    def resolve(self) -> W:
        return self.wrapped_dependency.resolve()


class DependencyTable:
    def __init__(self, dependencies: dict[str, DependencyProtocol[Any]] | None = None):
        self._dependencies: dict[str, DependencyProtocol[Any]] = dependencies or {}

    def add_dependency(self, name: str, dependency: DependencyProtocol[Any]):
        if name in self._dependencies:
            raise ValueError(f"Dependency {name!r} already exists")
        self._dependencies[name] = dependency

    def resolve(self, name: str) -> Any:
        if name not in self._dependencies:
            raise ValueError(f"Dependency {name!r} not found")
        return self._dependencies[name].resolve()

    def __getattr__(self, name: str) -> Any:
        return self.resolve(name)


class RouterMeta(type):
    def __new__(metacls, name, bases, namespace, /, **kwds):
        # print(f"Creating class {name} with RouterMeta")
        # print(f"Namespace: {namespace}")
        cls = super().__new__(metacls, name, bases, namespace, **kwds)
        if name == "Router" and namespace.get("__module__") == __name__:
            cls.__routes_map__ = {}  # type: ignore
            return cls
        cls.__routes_map__ = create_url_map(namespace)  # type: ignore
        cls.__dependencies__ = collect_dependencies(namespace)  # type: ignore
        inheritables = {
            dep_name: value
            for dep_name, value in cls.__dependencies__.items()  # type: ignore
            if isinstance(value, InheritableDependency)
        }
        for handler in cls.__routes_map__.values():  # type: ignore
            if isinstance(handler, Router):
                # Inherit dependencies to sub-routers
                for dep_name, dep in inheritables.items():
                    if dep_name not in handler.__dependencies__:
                        handler.__dependencies__[dep_name] = dep.wrapped_dependency

        return cls


@dataclass
class MiddlewareContext:
    # router: Router
    request: Request
    values: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    dependencies: DependencyTable = field(default_factory=DependencyTable)


class Router(metaclass=RouterMeta):
    __root_point_to__: str | None = None
    __special_path_routes__: dict[str, str] = {}
    __dependencies__: dict[str, DependencyProtocol[Any]] = {}
    __middlewares__: list[Middleware] = []

    if TYPE_CHECKING:
        __routes_map__: dict[str, Route]

    @classmethod
    def routes_map(cls) -> dict[str, Route]:
        return cls.__routes_map__

    @property
    def dependencies(self) -> DependencyTable:
        return DependencyTable(self.__dependencies__)

    @property
    def per_instance_middlewares(self) -> list[Middleware]:
        # instance must define __instance_middlewares__ = [...] to have per-instance middlewares
        return getattr(self, "__instance_middlewares__", [])

    @property
    def middlewares(self) -> list[Middleware]:
        # class middlewares are defined in __middlewares__, instance middlewares are defined in __instance_middlewares__
        return self.__middlewares__ + self.per_instance_middlewares


def _get_route_middlewares(
    handler: RouterBoundRouteCallable | RouterSelfRouteCallable,
) -> list[Middleware]:
    return getattr(handler, "__route_middlewares__", [])


def _discover_middlewares(
    routers: list[Router], handler: RouterBoundRouteCallable
) -> tuple[Middleware, ...]:
    # Discover middlewares for the given handler by traversing the middleware tree
    middlewares = []
    for router in routers:
        middlewares.extend(router.middlewares)
    middlewares.extend(_get_route_middlewares(handler))
    return tuple(middlewares)


class RoutingManager:
    def __init__(self):
        self.routing = Map()
        self.full_path_to_router: dict[str, RouterBoundRouteCallable] = {}
        self.middleware_tree_per_router: dict[
            RouterBoundRouteCallable, tuple[Middleware, ...]
        ] = {}

    def add_router(
        self,
        prefix: str,
        router: Router,
        parent_routers: list[Router] | None = None,
    ):
        parents = parent_routers or []

        for path, handler in type(router).routes_map().items():
            full_path = f"{prefix}/{path}".replace("//", "/")
            if not full_path.startswith("/"):
                full_path = "/" + full_path

            if isinstance(handler, Router):
                self.add_router(full_path, handler, parents + [router])
            else:
                bound_handler = getattr(router, handler.__name__)
                self.routing.add(Rule(full_path, endpoint=full_path))
                self.full_path_to_router[full_path] = bound_handler
                self.middleware_tree_per_router[bound_handler] = _discover_middlewares(
                    parents + [router], bound_handler
                )

    def create_wrapped_handler(self, handler: RouterBoundRouteCallable) -> FinalHandler:
        middlewares = self.middleware_tree_per_router.get(handler, ())
        return _wrap_middlewares(handler, middlewares)

    def handle_request(self, request: Request) -> Response:
        adapter = self.routing.bind_to_environ(request.environ)
        try:
            full_path, values = adapter.match()
        except HTTPException as e:
            return e.get_response(request)
        except Exception as e:
            return Response(f"Error: {e}", mimetype="text/plain", status=500)
        else:
            handler = self.full_path_to_router.get(full_path, None)
            if handler is None:
                return NotFound().get_response(request)
            router = cast(Router, handler.__self__)
            wrapped_handler = self.create_wrapped_handler(handler)
            context = MiddlewareContext(
                request=request, values=dict(values), dependencies=router.dependencies
            )
            return wrapped_handler(context)


class Server:
    def __init__(
        self, root_router: Router, middlewares: Sequence[Middleware] | None = None
    ):
        self.routing_manager = RoutingManager()
        self.routing_manager.add_router("", root_router)
        self.middlewares = tuple(middlewares or [])

    def _main_handler(self, request: Request) -> Response:
        return self.routing_manager.handle_request(request)

    @Request.application  # type: ignore
    def app(self, request: Request) -> Response:
        context = MiddlewareContext(request=request)
        wrapped_handler = _wrap_middlewares(self._main_handler, self.middlewares)
        return wrapped_handler(context)
