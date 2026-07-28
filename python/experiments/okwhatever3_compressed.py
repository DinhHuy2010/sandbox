# pyright: ignore
# ruff: noqa
"""
This module provides a collection of utility functions and classes for control flow, error handling, and context management in Python. It includes implementations of logical gates, conditional execution, loop control, and error handling mechanisms. The main function demonstrates the usage of these utilities with a simple example.
"""

_new_exception_cls = lambda name: type(
    name, (Exception,), {"__module__": f"{__name__}._exceptions"}
)

names = type(
    "_MagicNamesMap",
    (),
    {
        "__init__": lambda self: setattr(self, "_pkgutil", None),
        "_resolve": lambda self, key: (
            self._pkgutil or setattr(self, "_pkgutil", __import__("pkgutil")),
            simple_cond(
                isinstance(key, str),
                lambda: self._pkgutil.resolve_name(key),
                lambda: simple_cond(
                    isinstance(key, tuple),
                    lambda: tuple(self._pkgutil.resolve_name(k) for k in key),
                    lambda: error(ValueError("Invalid key for _MagicNamesMap")),
                ),
            ),
        )[-1],
        "__getitem__": lambda self, key: self._resolve(key),
        "__getattr__": lambda self, key: self[key],
        "__call__": lambda self, key: self[key],
    },
)()
LoopBreak, LoopContinue = (
    _new_exception_cls("LoopBreak"),
    _new_exception_cls("LoopContinue"),
)

evaluate = lambda code, /, globals=None, locals=None: eval(code, globals, locals)
execute = lambda code, /, globals=None, locals=None: (
    locals := locals or {},
    globals := globals or {},
    exec(code, globals, locals),
    locals,
)[-1]
cc_exec = lambda code: compile(code, "<string>", "exec")
cc_eval = lambda code: compile(code, "<string>", "eval")

nil = lambda *args, **kwargs: None
simple_cond = lambda cond, true, false=nil: (false, true)[bool(cond)]()
and_gate = lambda a, b: a and b
or_gate = lambda a, b: a or b
not_gate = lambda a: not a
xor_gate = lambda a, b: bool(a) != bool(b)
nand_gate = lambda a, b: not (a and b)
nor_gate = lambda a, b: not (a or b)
xnor_gate = lambda a, b: bool(a) == bool(b)
complex_cond = lambda *args: (
    CondMatched := names.dataclasses.make_dataclass(
        "CondMatched",
        [("value", object)],
        bases=(Exception,),
        namespace={"__module__": __name__},
    ),
    on_error(
        lambda: foreach(
            args,
            lambda arg: simple_cond(
                callable(arg),
                lambda: error(CondMatched(arg())),
                lambda: simple_cond(
                    arg[0],
                    lambda: error(CondMatched(arg[1]())),
                    nil,
                ),
            ),
        ),
        (CondMatched, lambda e: e.value),
    ),
)[-1]
meanwhile = lambda cond, body, else_=None: (
    names.collections.deque(
        iter(
            lambda: (
                c := cond(),
                on_error(
                    lambda: simple_cond(c, lambda: (body(), True)[1], lambda: False),
                    (LoopContinue, lambda _: True),
                    (LoopBreak, lambda _: False),
                ),
            )[-1],
            False,
        ),
        maxlen=0,
    ),
    simple_cond(else_ is not None, else_, nil),
    None,
)[-1]
foreach = lambda iterable, body, else_=None: (
    EndOfLoop := _new_exception_cls("EndOfLoop"),
    on_error(
        lambda: names.collections.deque(
            map(
                lambda x: on_error(
                    lambda: (body(x), None)[1],
                    (LoopContinue, lambda _: None),
                    (LoopBreak, lambda _: error(EndOfLoop())),
                ),
                iterable,
            ),
            maxlen=0,
        ),
        (EndOfLoop, lambda _: None),
        else_block=lambda: simple_cond(else_ is not None, else_, nil),
    ),
    None,
)[-1]
error = lambda exc, from_=None: execute(
    """raise exc from from_""", {}, {"exc": exc, "from_": from_}
)
_on_error_impl = execute(
    """def _on_error_impl(func, /, *handlers_args, else_block=None, finally_block=None):
    NoHandlerFound = _new_exception_cls("NoHandlerFound")
    HandlerFound = names.dataclasses.make_dataclass("HandlerFound",[("value", object)],bases=(Exception,),namespace={"__module__": __name__})

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
            lambda: else_block(),
            nil,
        )

        # 4. Fire the finally_block absolutely no matter what
        simple_cond(
            finally_block is not None,
            lambda: finally_block(),
            nil,
        )

        # 5. Re-raise any unhandled exceptions after cleanup finishes
        simple_cond(
            uncaught_exception is not None,
            lambda: error(uncaught_exception),
            nil,
        )

    # Return the handler's output if an error was caught, else the try output
    return simple_cond(
        has_error, lambda: handler_result[0], lambda: execution_result[0]
    )""",
    globals(),
    locals(),
)["_on_error_impl"]
on_error = lambda func, /, *handlers_args, else_block=None, finally_block=None: (
    _on_error_impl(
        func,
        *handlers_args,
        else_block=else_block,
        finally_block=finally_block,
    )
)
context_manager = lambda object, container: (
    # 1. Enter the context manager and capture the target resource
    value := object.__enter__(),
    # Trackers to manage exception handling state cleanly across lambdas
    suppress_exception := [False],
    on_error(
        # Try block: Execute the container callback with the entered resource
        lambda: container(value),
        # Except block: Catch any exception and pass it to the context's __exit__
        (
            BaseException,
            lambda e: simple_cond(
                object.__exit__(type(e), e, e.__traceback__),
                lambda: (
                    suppress_exception.clear(),
                    suppress_exception.append(True),
                )[1],
                lambda: error(e),  # Re-raise if __exit__ returns False/None
            ),
        ),
        # Else block: Only triggers if NO exception was raised
        else_block=lambda: object.__exit__(None, None, None),
        # Finally block: We don't need one here because __exit__ was already
        # cleanly routed to handle either the error path OR the success path!
    ),
)[-1]

__assertion_sentiel = object()
assertion = lambda condition, message=__assertion_sentiel: simple_cond(
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

asyncize = lambda f: lambda *a, **k: names["asyncio:to_thread"](f, *a, **k)
syncize = lambda f: (
    lambda *a, **k: on_error(
        # Try block: Check if an event loop is already running
        lambda: names["asyncio:get_running_loop"](),
        # Except block: If a RuntimeError occurs, no loop is running -> run safely!
        (RuntimeError, lambda _: names["asyncio:run"](f(*a, **k))),
        # Else block: If get_running_loop succeeds, use your custom context_manager
        else_block=lambda: context_manager(
            names["concurrent.futures:ThreadPoolExecutor"](),
            lambda executor: executor.submit(names["asyncio:run"], f(*a, **k)).result(),
        ),
    )
)
cls = lambda name, bases=(), namespace=None, extra_body=None, kwds=None: (
    module_name := names.inspect.currentframe().f_back.f_globals["__name__"],
    names.types.new_class(
        name,
        bases,
        kwds or {},
        exec_body=lambda ns: (
            ns.update(
                __module__=module_name,
                **(namespace or {}),
            ),
            simple_cond(extra_body is not None, lambda: extra_body(ns), nil),
            None,
        )[-1],
    ),
)[-1]


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
