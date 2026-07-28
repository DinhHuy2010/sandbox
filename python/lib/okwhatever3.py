# pyright: standard
"""
This module provides a collection of utility functions and classes for control flow, error handling, and context management in Python. It includes implementations of logical gates, conditional execution, loop control, and error handling mechanisms. The main function demonstrates the usage of these utilities with a simple example.
"""

import asyncio
import inspect
from collections import deque
from contextlib import AbstractContextManager
from importlib import import_module
import pkgutil
from types import new_class
from typing import Any, Awaitable, Callable, Coroutine, Iterable

type ConditionalCallable = Callable[[], object]
type Conditional = object
type Callback[T] = Callable[[], T]


class LoopBreak(Exception):
    def __str__(self):
        return "This loop should break"


class LoopContinue(Exception):
    def __str__(self):
        return "This loop should continue"


def nil(*args: Any, **kwargs: Any) -> None:
    pass


def simple_cond[T, F](
    cond: Conditional, true: Callback[T], false: Callback[F] = nil
) -> T | F:
    return (false, true)[bool(cond)]()


def and_gate[A, B](a: A, b: B) -> A | B:
    return a and b


def or_gate[A, B](a: A, b: B) -> A | B:
    return a or b


def not_gate(a: object) -> bool:
    return not a


def xor_gate(a: object, b: object) -> bool:
    return bool(a) != bool(b)


def nand_gate(a: object, b: object) -> bool:
    return not (a and b)


def nor_gate(a: object, b: object) -> bool:
    return not (a or b)


def xnor_gate(a: object, b: object) -> bool:
    return bool(a) == bool(b)


def complex_cond(
    *args: tuple[Conditional, Callback[object]] | Callback[object],
) -> object:
    class CondMatched(Exception):
        def __init__(self, value: object):
            self.value = value

    def loop_body(arg):
        return simple_cond(
            callable(arg),
            lambda: error(CondMatched(arg())),
            lambda: simple_cond(
                arg[0],
                lambda: error(CondMatched(arg[1]())),
                nil,
            ),
        )

    return on_error(
        lambda: foreach(args, loop_body),
        (CondMatched, lambda e: e.value),
    )


def meanwhile(
    cond: Callback[Conditional],
    body: Callback[object],
    else_: Callback[object] | None = None,
) -> None:
    def loop_body():
        c = cond()
        try:
            return simple_cond(c, lambda: (body(), True)[1], lambda: False)
        except LoopContinue:
            return True
        except LoopBreak:
            return False

    deque(iter(loop_body, False), maxlen=0)
    simple_cond(else_ is not None, else_, nil)  # type: ignore


def foreach[T](
    iterable: Iterable[T],
    body: Callable[[T], None],
    else_: Callback[object] | None = None,
):
    class EndOfLoop(Exception):
        pass

    def loop_body(x):
        try:
            body(x)
            return None
        except LoopContinue:
            return None
        except LoopBreak:
            raise EndOfLoop()

    try:
        deque(map(loop_body, iterable), maxlen=0)
    except EndOfLoop:
        pass
    else:
        simple_cond(else_ is not None, else_, nil)  # type: ignore


def error(exc: BaseException, from_: BaseException | None = None) -> None:
    raise exc from from_


def on_error[T, Exc](
    func: Callback[T],
    /,
    *handlers_args: tuple[type[Exc], Callable[[Exc], Any]],
    else_block: Callback[object] | None = None,
    finally_block: Callback[object] | None = None,
) -> T | Any:
    class NoHandlerFound(Exception):
        pass

    class HandlerFound(Exception):
        def __init__(self, value):
            self.value = value

    # State containers to track what happened inside our expression scope
    execution_result = []
    uncaught_exception = None
    handler_result = []
    has_error = False

    try:
        # 1. Try running the primary function
        execution_result.append(func())
    except BaseException as e:
        has_error = True

        def handle_exception(ha, e=e):
            exc_type, handler = ha
            simple_cond(
                isinstance(e, exc_type),
                lambda: error(HandlerFound(handler)),
                nil,
            )

        try:
            # 2. Look for a matching exception handler
            foreach(handlers_args, handle_exception)
            raise NoHandlerFound() from e
        except HandlerFound as hf:
            # Handler matched! Save its result safely
            handler_result.append(hf.value(e))
        except NoHandlerFound:
            # No handler matched. Track the exception to re-raise later
            uncaught_exception = e
    finally:
        # 3. Fire the else_block ONLY if no exception ever occurred
        simple_cond(
            (not has_error) and (else_block is not None),
            lambda: else_block(),  # type: ignore
            nil,
        )

        # 4. Fire the finally_block absolutely no matter what
        simple_cond(
            finally_block is not None,
            lambda: finally_block(),  # type: ignore
            nil,
        )

        # 5. Re-raise any unhandled exceptions after cleanup finishes
        simple_cond(
            uncaught_exception is not None,
            lambda: error(uncaught_exception),  # type: ignore
            nil,
        )

    # Return the handler's output if an error was caught, else the try output
    return simple_cond(
        has_error, lambda: handler_result[0], lambda: execution_result[0]
    )


def context_manager[T, F](
    object: AbstractContextManager[T], container: Callable[[T], F]
) -> F:
    # 1. Enter the context manager and capture the target resource
    value = object.__enter__()

    # Trackers to manage exception handling state cleanly across lambdas
    suppress_exception = [False]

    return on_error(
        # Try block: Execute the container callback with the entered resource
        lambda: container(value),
        # Except block: Catch any exception and pass it to the context's __exit__
        (
            BaseException,
            lambda e: simple_cond(
                object.__exit__(type(e), e, e.__traceback__),
                lambda: (suppress_exception.clear(), suppress_exception.append(True))[
                    1
                ],
                lambda: error(e),  # Re-raise if __exit__ returns False/None
            ),
        ),
        # Else block: Only triggers if NO exception was raised
        else_block=lambda: object.__exit__(None, None, None),
        # Finally block: We don't need one here because __exit__ was already
        # cleanly routed to handle either the error path OR the success path!
    )


__assertion_sentiel = object()


def assertion(condition: Conditional, message: object = __assertion_sentiel) -> None:
    simple_cond(
        condition,
        nil,
        lambda: error(
            simple_cond(
                message is not __assertion_sentiel,
                lambda: AssertionError(message),
                lambda: AssertionError(),
            )
        ),
    )


class _MagicModuleMap:
    def __getitem__(self, key):
        match key:
            case str():
                return import_module(key)
            case (str(), str()):
                module_name, attr_name = key
                module = import_module(module_name)
                return getattr(module, attr_name)
            case _:
                error(ValueError("Invalid key for _MagicModuleMap"))

    def __getattr__(self, name):
        return import_module(name)

    def __call__(self, key):
        return self[key]


class _MagicNamesMap:
    def __getitem__(self, key):
        match key:
            case str():
                return pkgutil.resolve_name(key)
            case tuple():
                return tuple(pkgutil.resolve_name(k) for k in key)
            case _:
                error(ValueError("Invalid key for _MagicNamesMap"))

    def __call__(self, key):
        return self[key]


imports = _MagicModuleMap()
names = _MagicNamesMap()


def asyncize[**P, Return](func: Callable[P, Return]) -> Callable[P, Awaitable[Return]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Return:
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


def syncize[**P, Return](
    func: Callable[P, Coroutine[Any, Any, Return]],
) -> Callable[P, Return]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Return:
        try:
            # If this succeeds, an event loop is already running
            asyncio.get_running_loop()

            # Since we can't use asyncio.run() here, we can execute the
            # coroutine in a separate temporary thread with its own loop.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, func(*args, **kwargs))
                return future.result()

        except RuntimeError:
            # No event loop is running; it's perfectly safe to use asyncio.run()
            return asyncio.run(func(*args, **kwargs))

    return wrapper


def evaluate(
    code: Any, /, globals: dict | None = None, locals: dict | None = None
) -> Any:
    return eval(code, globals, locals)


def execute(
    code: Any, /, globals: dict | None = None, locals: dict | None = None
) -> Any:
    return (
        locals := locals or {},
        globals := globals or {},
        exec(code, globals, locals),
        locals,
    )[-1]


def cc_eval(code: Any) -> Any:
    return compile(code, "<string>", "eval")


def cc_exec(code: Any) -> Any:
    return compile(code, "<string>", "exec")


def cls(
    name: str,
    bases: tuple[type, ...] = (),
    namespace: dict | None = None,
    extra_body: Callable[[dict], None] | None = None,
    kwds: dict | None = None,
) -> type:
    caller_frame = inspect.currentframe().f_back  # type: ignore
    caller_module = caller_frame.f_globals["__name__"]  # type: ignore
    return new_class(
        name,
        bases,
        kwds,
        exec_body=lambda ns: (
            ns.update(__module__=caller_module),
            ns.update(namespace or {}),
            simple_cond(extra_body is not None, lambda: extra_body(ns), nil),  # type: ignore
            None,
        )[-1],
    )


def main():
    print("This is the main module")
    simple_cond(
        1 > 0,
        lambda: print("1 is greater than 0"),
        lambda: print("1 is not greater than 0"),
    )
    complex_cond(
        (False, lambda: print("This will not be printed")),
        (False, lambda: print("This will be printed")),
        lambda: print("Else block"),
    )


simple_cond(__name__ == "__main__", main, nil)
