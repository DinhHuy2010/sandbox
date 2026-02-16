# type: ignore
# ruff: noqa
# fmt: off

from types import SimpleNamespace

import httpx


def _api_info(data):
    return SimpleNamespace(**data)


BaseAPI = type("BaseAPI", (SimpleNamespace,), {})


def with_info(d=None, /, **ds):
    if d is None:
        d = {}
    d.update(ds)
    return type(
        "__base_api_with_info__",
        (BaseAPI,),
        {"__about__": _api_info(d)},
    )

def return_as_simplens(func):
    def compose(d):
        if isinstance(d, dict):
            return SimpleNamespace({k: compose(v) for k, v in d.items()})
        elif isinstance(d, list):
            return [compose(i) for i in d]
        else:
            return d
        
    def wrapper(*args, **kwargs):
        return compose(func(*args, **kwargs))
    return wrapper

class MDRead(with_info(title="Metadata Read API", version="1.0")):
    get = return_as_simplens(lambda self, **_: self.client.get(f"https://archive.org/metadata/{_['id']}").json())


def new(api, /, **params):
    if api in {"mdread", "metadata_read"}:
        return MDRead(**params)
    raise ValueError(f"Unknown API: {api}")


reader = new("mdread", client=httpx.Client())
p = reader.get(id="stats")
print(p)
