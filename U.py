from __future__ import annotations
from typing import Any


class Methods:
    def __init__(self):
        self.__registry__ = {}

    def __getattr__(self, name: str):
        def decorator(func):
            self.__registry__[name] = func
            return func

        return decorator


class App:
    def __init__(self, app_func):
        self.app_func = app_func
        self.methods = Methods()

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        func_name = request.get("function")
        func = self.methods.__registry__.get(func_name)
        if func is None:
            return self.app_func(request)
        return func(request)


def create_app(app_func):
    return App(app_func)


@create_app
def app(request: dict[str, Any]) -> dict[str, Any]:
    return {"error": "Method not found"}


@app.methods.main
def main(request: dict[str, Any]):
    return {"message": "Hello, World!"}


@app.methods.update_board
def update_board(request: dict[str, Any]):
    board = request.get("state", {}).get("board", [])
    # Here you would typically update the board state based on the request
    return {"message": "Board updated", "board": board}
