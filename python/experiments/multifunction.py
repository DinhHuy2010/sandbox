from inspect import Parameter, signature
from typing import Any, Callable

type _F = Callable[..., Any]


def multifunction(*fs: _F) -> _F:
    if not fs:
        raise ValueError("At least one function must be provided")

    sigs = [(signature(f), f) for f in fs]

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        for sig, f in sigs:
            print(f"trying {f.__name__} with signature {sig}")
            try:
                sig.bind(*args, **kwargs)
            except TypeError:
                continue
            else:
                print(f"matched {f.__name__}{sig}")
                return f(*args, **kwargs)
        raise TypeError("No matching function found")

    return wrapper


def multifunction_smart(*funcs: _F) -> _F:
    if not funcs:
        raise ValueError("At least one function required")

    sigs = [(signature(f), f) for f in funcs]

    def score(sig, bound):
        params = sig.parameters
        score = 0

        for name, param in params.items():
            if name in bound.arguments:
                score += 2  # argument matched

                # prefer non-default usage
                if param.default is not Parameter.empty:
                    score -= 1  # default used

            # penalize *args and **kwargs
            if param.kind in (
                Parameter.VAR_POSITIONAL,
                Parameter.VAR_KEYWORD,
            ):
                score -= 1

        return score

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        winner = -1, None

        for sig, f in sigs:
            try:
                bound = sig.bind(*args, **kwargs)
            except TypeError:
                continue
            else:
                s = score(sig, bound)
                if s > winner[0]:
                    print(f"found better match: {f.__name__}{sig}")
                    winner = s, f

        if winner[1] is None:
            raise TypeError("No matching function found")

        # highest score wins
        return winner[1](*args, **kwargs)

    return wrapper

def multifunction_smart_2(*funcs: _F) -> _F:
    sigs = [(signature(f), f) for f in funcs]

    def score(sig, bound):
        params = sig.parameters

        required = 0
        defaults_used = 0
        var_absorbed = 0

        # Count required matches
        for name, param in params.items():
            if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
                continue

            if name in bound.arguments:
                if param.default is Parameter.empty:
                    required += 1
                else:
                    defaults_used += 1

        # Count how many args got swallowed by *args/**kwargs
        for name, value in bound.arguments.items():
            param = params[name]
            if param.kind == Parameter.VAR_POSITIONAL:
                var_absorbed += len(value)
            elif param.kind == Parameter.VAR_KEYWORD:
                var_absorbed += len(value)

        return (
            required,           # maximize
            -defaults_used,     # minimize
            -var_absorbed,      # minimize
        )

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        candidates = []

        for sig, f in sigs:
            try:
                bound = sig.bind(*args, **kwargs)
            except TypeError:
                continue
            candidates.append((score(sig, bound), f))

        if not candidates:
            raise TypeError("No matching function found")

        candidates.sort(reverse=True, key=lambda x: x[0])
        print(f"best match: {candidates[0][1].__name__} with score {candidates[0][0]}")
        return candidates[0][1](*args, **kwargs)

    return wrapper

def f1():
    print("f1 called")


def f2(a, b):
    print(f"f2 called with a={a}, b={b}")


def f3(a, b, c=None):
    print(f"f3 called with a={a}, b={b}, c={c}")


def f4(a=None, b=None, c=None):
    print(f"f4 called with a={a}, b={b}, c={c}")

def f5(*args, **kwargs):
    print(f"f5 called with args={args}, kwargs={kwargs}")

f = multifunction_smart_2(f1, f2, f3, f4, f5)
f()
f(1, 2)
f(1, 2, 3)
f(a=1, b=2)
f(a=1, b=2, c=3)
f(1, b=2, c=3)
f(b=2, c=3)
f(1, 2, 3, 4, x=5)
