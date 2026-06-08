import ast
from inspect import getsource


def on_error_impl(func, /, *handlers_args, else_block=None, finally_block=None):
    caught = False
    try:
        return func()
    except BaseException as e:
        for exc_type, handler in handlers_args:
            if isinstance(e, exc_type):
                caught = True
                return handler(e)
        raise
    finally:
        if else_block is not None and not caught:
            else_block()
        if finally_block is not None:
            finally_block()


TARGET = getsource(on_error_impl)
tree = ast.parse(TARGET)
names = set()
for node in ast.walk(tree):
    names.add(type(node).__name__)
names.add("fix_missing_locations")
names = sorted(names)
print(
    ", ".join(names), "=", "names[" + ", ".join(f'"ast:{name}"' for name in names) + "]"
)
print("__on_error_impl_tree =", ast.dump(tree))
