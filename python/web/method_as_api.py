from typing import Callable, MutableMapping

from orjson import dumps
from pydantic import JsonValue
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import Request, Response


def Constant(d: dict[str, JsonValue]) -> Callable[[], MutableMapping[str, JsonValue]]:
    def factory() -> MutableMapping[str, JsonValue]:
        return d

    return factory


class DictAPI:
    def __init__(
        self, mm_factory: Callable[[], MutableMapping[str, JsonValue]]
    ) -> None:
        self.map = Map(
            [
                Rule("/keys", methods=["GET", "PATCH"], endpoint="keys"),
                Rule("/keys/<key>", methods=["GET", "DELETE", "PUT"], endpoint="key"),
                Rule("/clear", methods=["POST"], endpoint="clear"),
                Rule("/size", methods=["GET"], endpoint="size"),
                Rule("/contains/<key>", methods=["GET"], endpoint="contains"),
                Rule("/items", methods=["GET"], endpoint="items"),
            ],
        )
        self._storage: MutableMapping[str, JsonValue] = mm_factory()

    def dispatch_request(self, request: Request) -> Response:
        adapter = self.map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            handler = getattr(self, f"handle_{endpoint}")
            return handler(request, **values)
        except HTTPException as e:
            return e.get_response(request)
        except Exception as e:
            return Response(str(e), status=500)

    def handle_keys(self, request: Request) -> Response:
        match request.method:
            case "GET":
                keys = list(self._storage.keys())
                return Response(dumps(keys), mimetype="application/json")
            case "PATCH":
                data = request.get_json()
                if not isinstance(data, dict):
                    return Response("Invalid JSON", status=400)
                self._storage.update(data)
                return Response(status=204)

    def handle_key(self, request: Request, key: str) -> Response:
        match request.method:
            case "GET":
                if key not in self._storage:
                    return Response("Key not found", status=404)
                value = self._storage[key]
                return Response(dumps(value), mimetype="application/json")
            case "DELETE":
                if key not in self._storage:
                    return Response("Key not found", status=404)
                del self._storage[key]
                return Response(status=204)
            case "PUT":
                data = request.get_json()
                if data is None:
                    return Response("Invalid JSON", status=400)
                self._storage[key] = data
                return Response(status=204)

    def handle_clear(self, request: Request) -> Response:
        self._storage.clear()
        return Response(status=204)

    def handle_size(self, request: Request) -> Response:
        size = len(self._storage)
        return Response(dumps(size), mimetype="application/json")

    def handle_contains(self, request: Request, key: str) -> Response:
        contains = key in self._storage
        return Response(dumps(contains), mimetype="application/json")

    def handle_items(self, request: Request) -> Response:
        def stream():
            for key, value in self._storage.items():
                yield dumps({"key": key, "value": value}) + b"\n"

        return Response(stream(), mimetype="application/json")


if __name__ == "__main__":
    from werkzeug.serving import run_simple

    api = DictAPI(Constant({"foo": "bar", "baz": 42}))
    run_simple("localhost", 5000, Request.application(api.dispatch_request))
