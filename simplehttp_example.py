
from simplehttp import (
    InheritableDependency,
    Router,
    Request,
    Response,
    Dependency,
    special_path,
    force_as_route,
)


class APIRouter(Router):
    __middlewares__ = [
        lambda ctx, next: print(f"API Middleware: {ctx.request.path}") or next(ctx),
        lambda ctx, next: print("Another API Middleware") or next(ctx),
        lambda ctx, next: print("Final API Middleware") or next(ctx),
        lambda ctx, next: (
            print("End of API Middleware chain")
            or Response("Blocked by API Middleware", mimetype="text/plain", status=403)
        ),
    ]

    def data(self, request: Request) -> Response:  # /data (or /api/data)
        return Response("This is some data.", mimetype="application/json")


def get_db() -> str:
    return "Database Connection"


def get_cache() -> str:
    return "Cache Connection"


class UserMeRouter(Router):
    __root_point_to__ = "_index"  # / -> _index()
    # @special_path("")  # matches /user/me
    @force_as_route
    def _index(self, request: Request) -> Response:
        return Response(f"This is the user info (cache: {self.dependencies.cache})", mimetype="text/plain")


class UserRouter(Router):
    __special_path_routes__ = {
        # "<id>": "_profile_for",
        # This is a special path that matches /user/<id> and routes to _profile_for()
    }
    __dependencies__ = {"db": Dependency(get_db)}
    __middlewares__ = [
        lambda ctx, next: print(f"/user/me Middleware: {ctx.request.path}") or next(ctx)
    ]

    cache = InheritableDependency(Dependency(get_cache))

    me = UserMeRouter()  # /user/me -> UserMeRouter()

    @special_path("<id>")
    @force_as_route
    def _profile_for(
        self, request: Request, *, id: str = ...
    ) -> Response:  # /<id> (or /user/<id>)
        return Response(
            f"This is the user profile {id} (cache: {self.cache}).",
            mimetype="application/json",
        )


class Application(Router):
    __root_point_to__ = "index"  # / -> index()
    __middlewares__ = [
        lambda ctx, next: (
            print(f"Application Middleware: {ctx.request.path}") or next(ctx)
        )
    ]

    def index(self, request: Request) -> Response:  # /index
        return Response("Hello, World!", mimetype="text/plain")

    def about(self, request: Request) -> Response:  # /about
        return Response("This is a simple HTTP server.", mimetype="text/plain")

    api = APIRouter()  # /api -> APIRouter()
    user = UserRouter()  # /user -> UserRouter()


if __name__ == "__main__":
    from simplehttp import Server
    from werkzeug.serving import run_simple

    server = Server(
        Application(),
        middlewares=[lambda ctx, next: print("Global Middleware") or next(ctx)],
    )
    # pprint(server.middleware_tree_per_router)
    # # print(server.routing)
    # # print(server.routing._rules)

    run_simple("localhost", 8080, server.app)
