"""Werkzeug-backed implementation of the config schema in ``theserver.py``.

The public surface stays dict-first:

* native handlers receive a request dict
* native handlers return result dicts
* server setup comes from a config dict

Werkzeug supplies the WSGI request/response, routing, static-file, mounting,
and development-server pieces. Config ``middleware`` entries are WSGI
middleware factories: each referenced callable receives an app and returns an
app. The first configured middleware is the outermost middleware.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable, Mapping
from types import ModuleType
from typing import Any, Protocol, cast

from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.routing import Map, Rule
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response


Config = Mapping[str, Any]
RouteConfig = Mapping[str, Any]
ResultDict = Mapping[str, Any]
RequestDict = dict[str, Any]
StartResponse = Callable[..., Any]
WSGIApp = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]


class NativeHandler(Protocol):
    def __call__(self, request: RequestDict) -> ResultDict: ...


class MiddlewareFactory(Protocol):
    def __call__(self, app: WSGIApp) -> WSGIApp: ...


class ConfigError(ValueError):
    """Raised when the server config does not describe a usable app."""


def resolve_reference(reference: str, local_module: ModuleType | None = None) -> Any:
    """Resolve ``module:object`` or ``:object`` references from config."""
    module_name, separator, object_path = reference.partition(":")
    if not separator or not object_path:
        raise ConfigError(
            f"Reference {reference!r} must look like 'module:object' or ':object'."
        )

    if module_name:
        module = importlib.import_module(module_name)
    elif local_module is not None:
        module = local_module
    else:
        raise ConfigError(
            f"Reference {reference!r} needs a config module for local lookup."
        )

    obj: Any = module
    for name in object_path.split("."):
        try:
            obj = getattr(obj, name)
        except AttributeError as exc:
            raise ConfigError(
                f"Reference {reference!r} has no object component {name!r}."
            ) from exc
    return obj


def response_from_dict(result: ResultDict, *, native: bool = False) -> Response:
    """Turn a config or native response dict into a Werkzeug response."""
    if native and result.get("type") != "response":
        raise ConfigError("Native handlers must return a result with type='response'.")

    try:
        status = int(result["status"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError("Response dict must contain an integer status.") from exc

    headers = result.get("headers", {})
    if not isinstance(headers, Mapping):
        raise ConfigError("Response headers must be a mapping.")

    body = result.get("body", b"")
    if not isinstance(body, (bytes, bytearray, memoryview, str)):
        raise ConfigError("Response body must be bytes or text in this prototype.")

    return Response(body, status=status, headers=dict(headers))


def request_to_dict(request: Request, *, route: str) -> RequestDict:
    """Expose the native handler request boundary as a plain dict."""
    return {
        "method": request.method,
        "url": request.url,
        "path": request.path,
        "query_string": request.query_string,
        "headers": dict(request.headers.items()),
        "body": request.stream,
        "extra": {
            "route": route,
            "environ": request.environ,
        },
    }


def apply_response_headers(app: WSGIApp, headers: Mapping[str, str]) -> WSGIApp:
    """Add configured response headers to a WSGI app."""
    extra_headers = list(headers.items())

    def wrapped(environ: dict[str, Any], start_response: StartResponse):
        def add_headers(status: str, response_headers: list[tuple[str, str]], exc_info=None):
            return start_response(
                status,
                [*response_headers, *extra_headers],
                exc_info,
            )

        return app(environ, add_headers)

    return wrapped


def unsupported_asgi_app(prefix: str) -> WSGIApp:
    """Return a WSGI app that makes the WSGI-only ASGI boundary explicit."""

    def app(environ: dict[str, Any], start_response: StartResponse):
        response = Response(
            (
                f"ASGI route {prefix!r} cannot run inside this Werkzeug WSGI "
                "implementation."
            ),
            status=501,
            content_type="text/plain",
        )
        return response(environ, start_response)

    return app


def not_found_app(environ: dict[str, Any], start_response: StartResponse):
    return NotFound()(environ, start_response)


class ConfigServer:
    """Compile route config into one WSGI application."""

    def __init__(self, config: Config, *, config_module: ModuleType | None = None):
        self.config = config
        self.config_module = config_module
        self.route_specs = self._route_specs()
        self.exact_routes = Map(self._exact_rules())
        self.mounts = self._mount_apps()

    def _route_specs(self) -> Mapping[str, RouteConfig]:
        routes = self.config.get("routes")
        if not isinstance(routes, Mapping):
            raise ConfigError("Config must define routes as a mapping.")

        for path, route in routes.items():
            if not isinstance(path, str) or not path.startswith("/"):
                raise ConfigError(f"Route path {path!r} must start with '/'.")
            if not isinstance(route, Mapping):
                raise ConfigError(f"Route config for {path!r} must be a mapping.")
            if not isinstance(route.get("type"), str):
                raise ConfigError(f"Route config for {path!r} must define type.")
        return cast(Mapping[str, RouteConfig], routes)

    def _exact_rules(self) -> list[Rule]:
        rules: list[Rule] = []
        for path, route in self.route_specs.items():
            if route["type"] in {"static", "wsgi", "asgi"}:
                continue

            methods = route.get("methods")
            if methods is not None and not isinstance(methods, list):
                raise ConfigError(f"Route {path!r} methods must be a list.")
            rules.append(Rule(path, methods=methods, endpoint=path))
        return rules

    def _mount_apps(self) -> dict[str, WSGIApp]:
        mounts: dict[str, WSGIApp] = {}
        for prefix, route in self.route_specs.items():
            route_type = route["type"]
            if route_type == "wsgi":
                app = self._resolve_callable(route, "application", prefix)
                mounts[prefix] = cast(WSGIApp, app)
            elif route_type == "static":
                mounts[prefix] = self._static_app(route, prefix)
            elif route_type == "asgi":
                mounts[prefix] = unsupported_asgi_app(prefix)
        return mounts

    def _resolve_callable(self, route: RouteConfig, key: str, path: str) -> Callable[..., Any]:
        reference = route.get(key)
        if not isinstance(reference, str):
            raise ConfigError(f"Route {path!r} must define {key} as a reference.")

        obj = resolve_reference(reference, self.config_module)
        if not callable(obj):
            raise ConfigError(f"Reference {reference!r} for route {path!r} is not callable.")
        return obj

    def _static_app(self, route: RouteConfig, prefix: str) -> WSGIApp:
        directory = route.get("directory")
        if not isinstance(directory, str):
            raise ConfigError(f"Static route {prefix!r} must define directory.")

        app = cast(
            WSGIApp,
            SharedDataMiddleware(not_found_app, {"/": directory}),
        )
        headers = route.get("extra_response_headers", {})
        if not isinstance(headers, Mapping):
            raise ConfigError(
                f"Static route {prefix!r} extra_response_headers must be a mapping."
            )
        if headers:
            app = apply_response_headers(app, cast(Mapping[str, str], headers))
        return app

    def dispatch_exact(self, request: Request) -> Response:
        adapter = self.exact_routes.bind_to_environ(request.environ)
        try:
            path, _values = adapter.match()
        except HTTPException as exc:
            return exc.get_response(request)

        return self.dispatch_route(request, path, self.route_specs[path])

    def dispatch_route(self, request: Request, path: str, route: RouteConfig) -> Response:
        route_type = route["type"]
        if route_type == "simple":
            response = route.get("response")
            if not isinstance(response, Mapping):
                raise ConfigError(f"Simple route {path!r} must define response.")
            return response_from_dict(response)

        if route_type == "normal":
            handler = cast(NativeHandler, self._resolve_callable(route, "function", path))
            return response_from_dict(
                handler(request_to_dict(request, route=path)),
                native=True,
            )

        if route_type == "advanced":
            return self.dispatch_advanced(request, path, route)

        raise ConfigError(f"Exact route {path!r} has unsupported type {route_type!r}.")

    def dispatch_advanced(self, request: Request, path: str, route: RouteConfig) -> Response:
        cases = route.get("cases")
        if not isinstance(cases, Mapping):
            raise ConfigError(f"Advanced route {path!r} must define cases.")

        default: RouteConfig | None = None
        for condition, case in cases.items():
            if not isinstance(condition, str) or not isinstance(case, Mapping):
                raise ConfigError(f"Advanced route {path!r} has an invalid case.")
            if condition == "default":
                default = cast(RouteConfig, case)
                continue
            if self.case_matches(request, condition):
                return self.dispatch_route(request, path, cast(RouteConfig, case))

        if default is not None:
            return self.dispatch_route(request, path, default)
        return NotFound().get_response(request)

    @staticmethod
    def case_matches(request: Request, condition: str) -> bool:
        key, separator, value = condition.partition("=")
        if not separator:
            raise ConfigError(f"Advanced case condition {condition!r} needs '='.")
        if key == "method":
            return request.method == value
        if key.startswith("header."):
            return request.headers.get(key.removeprefix("header.")) == value
        raise ConfigError(f"Unknown advanced case condition {condition!r}.")

    @Request.application
    def exact_app(self, request: Request) -> Response:
        return self.dispatch_exact(request)

    def app(self) -> WSGIApp:
        return cast(WSGIApp, DispatcherMiddleware(self.exact_app, self.mounts))


def apply_config_middleware(
    app: WSGIApp,
    middleware_refs: Any,
    *,
    config_module: ModuleType | None,
) -> WSGIApp:
    if middleware_refs is None:
        return app
    if not isinstance(middleware_refs, list):
        raise ConfigError("Config middleware must be a list of references.")

    for reference in reversed(middleware_refs):
        if not isinstance(reference, str):
            raise ConfigError("Every middleware entry must be a reference string.")
        middleware = resolve_reference(reference, config_module)
        if not callable(middleware):
            raise ConfigError(f"Middleware reference {reference!r} is not callable.")
        app = cast(MiddlewareFactory, middleware)(app)
    return app


def create_app(config: Config, *, config_module: ModuleType | None = None) -> WSGIApp:
    """Create one WSGI app from a server config dict."""
    server = ConfigServer(config, config_module=config_module)
    return apply_config_middleware(
        server.app(),
        config.get("middleware"),
        config_module=config_module,
    )


def serve(config: Config, *, config_module: ModuleType | None = None, **kwargs: Any) -> None:
    """Run a config app with Werkzeug's development WSGI server."""
    host = config.get("host", "localhost")
    port = config.get("port", 8080)
    if not isinstance(host, str) or not isinstance(port, int):
        raise ConfigError("Config host must be text and port must be an integer.")
    run_simple(host, port, create_app(config, config_module=config_module), **kwargs)
