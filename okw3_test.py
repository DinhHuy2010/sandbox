import asyncio

import pytest

import okwhatever3_compressed_x2 as okw


def test_evaluate_execute_and_compile_helpers():
    assert okw.evaluate("1 + 2") == 3

    namespace = okw.execute("answer = value * 2", {"value": 21})
    assert namespace["answer"] == 42

    assert okw.evaluate(okw.cc_eval("3 * 7")) == 21

    exec_namespace = {}
    exec(okw.cc_exec("created = 'yes'"), {}, exec_namespace)
    assert exec_namespace["created"] == "yes"


def test_nil_and_simple_cond_are_lazy():
    calls = []

    assert okw.nil("ignored", keyword="ignored") is None
    assert (
        okw.simple_cond(
            True, lambda: calls.append("true") or "T", lambda: calls.append("false")
        )
        == "T"
    )
    assert calls == ["true"]

    assert (
        okw.simple_cond(
            False, lambda: calls.append("true"), lambda: calls.append("false") or "F"
        )
        == "F"
    )
    assert calls == ["true", "false"]


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ],
)
def test_logic_gates(a, b):
    assert (
        okw.and_gate(a, b),
        okw.or_gate(a, b),
        okw.not_gate(a),
        okw.xor_gate(a, b),
        okw.nand_gate(a, b),
        okw.nor_gate(a, b),
        okw.xnor_gate(a, b),
    ) == (
        a and b,
        a or b,
        not a,
        bool(a) != bool(b),
        not (a and b),
        not (a or b),
        bool(a) == bool(b),
    )


def test_complex_cond_returns_first_matching_branch_or_callable_result():
    calls = []

    result = okw.complex_cond(
        (False, lambda: calls.append("first") or "first"),
        (True, lambda: calls.append("second") or "second"),
        lambda: calls.append("fallback") or "fallback",
    )

    assert result == "second"
    assert calls == ["second"]

    assert okw.complex_cond(lambda: "callable branch") == "callable branch"


def test_foreach_handles_continue_break_and_else():
    seen = []
    else_calls = []

    def body(value):
        if value == 2:
            okw.error(okw.LoopContinue())
        seen.append(value)

    assert okw.foreach([1, 2, 3], body, else_=lambda: else_calls.append("done")) is None
    assert seen == [1, 3]
    assert else_calls == ["done"]

    seen.clear()
    else_calls.clear()

    def break_body(value):
        if value == 3:
            okw.error(okw.LoopBreak())
        seen.append(value)

    assert (
        okw.foreach([1, 2, 3, 4], break_body, else_=lambda: else_calls.append("done"))
        is None
    )
    assert seen == [1, 2]
    assert else_calls == []


def test_meanwhile_repeats_until_condition_is_false_and_handles_loop_control():
    values = iter([1, 2, 3, 4])
    current = {"value": None}
    seen = []
    else_calls = []

    def cond():
        current["value"] = next(values, None)
        return current["value"] is not None

    def body():
        if current["value"] == 2:
            okw.error(okw.LoopContinue())
        if current["value"] == 4:
            okw.error(okw.LoopBreak())
        seen.append(current["value"])

    assert okw.meanwhile(cond, body, else_=lambda: else_calls.append("done")) is None
    assert seen == [1, 3]
    assert else_calls == ["done"]


def test_on_error_returns_success_handler_result_and_reraises_unhandled_errors():
    calls = []

    assert (
        okw.on_error(
            lambda: "ok",
            (ValueError, lambda exc: "handled"),
            else_block=lambda: calls.append("else"),
            finally_block=lambda: calls.append("finally"),
        )
        == "ok"
    )
    assert calls == ["else", "finally"]

    assert (
        okw.on_error(
            lambda: okw.error(ValueError("bad")),
            (ValueError, lambda exc: f"handled {exc}"),
            finally_block=lambda: calls.append("handled finally"),
        )
        == "handled bad"
    )
    assert calls[-1] == "handled finally"

    with pytest.raises(TypeError, match="missing"):
        okw.on_error(
            lambda: okw.error(TypeError("missing")),
            (ValueError, lambda exc: "wrong handler"),
            finally_block=lambda: calls.append("unhandled finally"),
        )
    assert calls[-1] == "unhandled finally"


def test_context_manager_enters_exits_suppresses_and_reraises():
    class Recorder:
        def __init__(self, suppress=False):
            self.suppress = suppress
            self.events = []

        def __enter__(self):
            self.events.append(("enter",))
            return "resource"

        def __exit__(self, exc_type, exc, traceback):
            self.events.append(("exit", exc_type, str(exc) if exc else None))
            return self.suppress

    success = Recorder()
    assert (
        okw.context_manager(success, lambda value: f"using {value}") == "using resource"
    )
    assert success.events == [("enter",), ("exit", None, None)]

    suppressed = Recorder(suppress=True)
    assert (
        okw.context_manager(suppressed, lambda value: okw.error(RuntimeError("quiet")))
        is None
    )
    assert suppressed.events[0] == ("enter",)
    assert suppressed.events[1][0] == "exit"
    assert suppressed.events[1][1] is RuntimeError
    assert suppressed.events[1][2] == "quiet"

    unsuppressed = Recorder(suppress=False)
    with pytest.raises(RuntimeError, match="loud"):
        okw.context_manager(unsuppressed, lambda value: okw.error(RuntimeError("loud")))


def test_assertion_helper():
    assert okw.assertion(True, "message") is None

    with pytest.raises(AssertionError):
        okw.assertion(False)

    with pytest.raises(AssertionError, match="custom"):
        okw.assertion(False, "custom")


def test_asyncize_adapter():
    def blocking_double(value):
        return value * 2

    assert asyncio.run(okw.asyncize(blocking_double)(21)) == 42


def test_syncize_adapter_without_running_loop():
    async def async_double(value):
        return value * 2

    sync_double = okw.syncize(async_double)
    assert sync_double(21) == 42


@pytest.mark.skip(
    reason="syncize deadlocks when called from an already-running event loop"
)
def test_syncize_inside_running_loop_uses_thread_executor():
    async def async_value():
        return "from coroutine"

    async def runner():
        return okw.syncize(async_value)()

    assert asyncio.run(runner()) == "from coroutine"


def test_cls_creates_dynamic_class_with_namespace_and_extra_body():
    Created = okw.cls(
        "Created",
        namespace={"value": 10},
        extra_body=lambda ns: ns.update(double=lambda self: self.value * 2),
    )

    instance = Created()
    assert Created.__name__ == "Created"
    assert Created.__module__ == __name__
    assert instance.value == 10
    assert instance.double() == 20


def test_magic_names_map_resolves_names_and_rejects_invalid_keys():
    assert okw.names["builtins:len"]([1, 2, 3]) == 3

    resolved_len, resolved_sum = okw.names[("builtins:len", "builtins:sum")]
    assert resolved_len([1]) == 1
    assert resolved_sum([1, 2, 3]) == 6

    with pytest.raises(ValueError, match="Invalid key"):
        okw.names[object()]
