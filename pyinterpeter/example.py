# type: ignore
# ruff: noqa

x = 1 + 2
y = x**10
print("Hello, world!")
print(y.resolve())
o = __pihelper__.Future(y.resolve, args=tuple(), kwargs=dict()).resolve()
print(o)
if 3 > 1:
    print("3 is greater than 1")


def foo(a: int, b: str = "default") -> int:
    """This is a docstring for foo."""
    return 42


def nested():
    x = 10

    def inner():
        print(x)
        return "inner"

    return inner


def decorator(func):
    def wrapper(*args, **kwargs):
        print("Before calling the function")
        result = func(*args, **kwargs)
        print("After calling the function")
        return result

    return wrapper


@decorator
def decorated_function():
    print("Inside the decorated function")
    return "decorated result"


print(foo(0))
print(nested()())
print(decorated_function())
print([1, 2, 3, 4])