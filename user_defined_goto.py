# from contextlib import contextmanager
# import sys
# from typing import Any


# class Goto(Exception):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args)
#         self.kwargs = kwargs

#     def body(self, *args: Any, **kwargs: Any):
#         pass


# # @contextmanager
# def patch_goto():
#     handler = sys.excepthook

#     def new_handler(exc_type, exc_value, traceback):
#         # print("Custom exception handler called for:", exc_type)
#         if isinstance(exc_value, Goto):
#             exc_value.body(*exc_value.args, **exc_value.kwargs)
#         else:
#             handler(exc_type, exc_value, traceback)

#     sys.excepthook = new_handler
#     return handler


# class MyGoto(Goto):
#     def body(self, *args, **kwargs):
#         print("Goto body called with args:", args, "and kwargs:", kwargs)

# class MyOtherGoto(Goto):
#     def body(self, a, b):
#         print(f"{a} + {b} =", a + b)

# patch_goto()
# # raise MyGoto(1, 2, key="value")
# raise MyOtherGoto(3, 4)

from dataclasses import dataclass


@dataclass
class OK[T](Exception):
    value: T


def fib(n: int):
    x, y = 0, 1
    for _ in range(n):
        x, y = y, x + y
    raise OK(x)


for _ in range(100):
    try:
        fib(_)
    except OK as e:
        print(e.value)
