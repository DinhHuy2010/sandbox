# type: ignore


def _getversion(_):
    import sys

    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


depenencies = {
    None: {"getPython": {"type": "method_move_ref", "next_ref": "python"}},
    "python": {
        "getVersion": {"type": "method", "function": _getversion},
        "listAdd": {"type": "method", "function": lambda x, y: x + [y]},
        "listRemove": {
            "type": "method",
            "function": lambda _, x, y: [item for item in x if item != y],
            "initList": {"type": "method", "function": lambda _: []},
        },
    },
}


class DI:
    def __init__(self):
        self.__refs__ = []

    def __getattr__(self, name):
        if name in depenencies.get(None, {}):
            ref_info = depenencies[None][name]
            if ref_info["type"] == "method_move_ref":
                next_ref_name = ref_info["next_ref"]
                next_ref = DI()
                next_ref.__refs__ = self.__refs__ + [next_ref_name]
                return lambda: next_ref
        else:
            current_ref = self.__refs__[-1] if self.__refs__ else None
            if current_ref and name in depenencies.get(current_ref, {}):
                method_info = depenencies[current_ref][name]
                if method_info["type"] == "method":
                    func = method_info["function"]
                    setattr(self, name, lambda *args, func=func: func(self, *args))
                    return getattr(self, name)
        raise AttributeError(f"'DI' object has no attribute '{name}'")


di = DI()
print(di.getPython().getVersion())
