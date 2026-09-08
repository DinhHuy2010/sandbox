from typing import TYPE_CHECKING

import okwhatever4 as o4

if TYPE_CHECKING:
    import fastapi
else:
    fastapi = o4.imports("fastapi")
app = fastapi.FastAPI()
app.add_api_route("/", lambda: {"message": "Hello World"}, methods=["GET"])


# get, set = o4.local(["get", "set"])
# set("test", 42)
# set("test3", 43)
# o = o4.on_error(lambda: get("test2"), (NameError, lambda exc: get("test")))
# print(o)
