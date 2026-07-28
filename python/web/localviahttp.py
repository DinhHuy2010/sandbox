# pyright: standard

from __future__ import annotations

from inspect import signature
import sys
from abc import ABC, abstractmethod
from typing import Annotated, Any, Callable, Concatenate, Self

from annotated_types import Predicate
from attrs import define, field
from pydantic import JsonValue
import pydantic

from python.lib.pydantic_attrs import validate_via_pydantic

type EventHandler[_RuntimeT: "BaseRuntime"] = Callable[
    Concatenate[_RuntimeT, ...], JsonValue | ForwardEmit[_RuntimeT] | None
]


class BaseRuntime[R: BaseRuntime[Any]](ABC):
    @abstractmethod
    def on(self, event: str) -> Callable[[EventHandler[R]], EventHandler[R]]:
        raise NotImplementedError("on method is not implemented in BaseRuntime")

    @abstractmethod
    def emit(self, event: str, *args: JsonValue, **kwargs: JsonValue) -> None:
        raise NotImplementedError("emit method is not implemented in BaseRuntime")

    def call(
        self, event: str, *args: JsonValue, **kwargs: JsonValue
    ) -> JsonValue | None:
        raise NotImplementedError("call method is not implemented in BaseRuntime")

    def trace(self, event: Event) -> None:
        raise NotImplementedError("trace method is not implemented in BaseRuntime")


@define
class RuntimeHandlers[RuntimeT: BaseRuntime[Any]]:
    runtime: RuntimeT
    event: Annotated[str, pydantic.StringConstraints(pattern=r"^[a-zA-Z0-9_.-]+$")] = (
        field(validator=validate_via_pydantic())
    )
    callbacks: dict[
        Annotated[str, Predicate(str.isidentifier)], EventHandler[RuntimeT]
    ] = field(factory=dict)

    def get_callback_name(self, callback: EventHandler[RuntimeT]) -> str:
        for attr in {"__name__", "__qualname__"}:
            try:
                name = getattr(callback, attr)
                break
            except AttributeError:
                continue
        else:
            return f"{self.event}/{id(callback):x}"
        return f"{self.event}/{name}"

    def do(self, callback: EventHandler[RuntimeT]) -> Self:
        self.callbacks[self.get_callback_name(callback)] = callback
        return self

    def trace(self, event: Event) -> None:
        self.runtime.trace(event)

    def _emit_with_tracing(
        self,
        callback_name: str,
        callback: EventHandler[RuntimeT],
        *args: JsonValue,
        **kwargs: JsonValue,
    ) -> None:
        event = Event(
            runtime=self.runtime,
            event=self.event,
            args=args,
            kwargs=kwargs,
            callback_name=callback_name,
        )
        self.trace(event)
        value = callback(self.runtime, *args, **kwargs)
        if isinstance(value, ForwardEmit):
            value.emit()

    def _call_with_tracing(
        self,
        callback_name: str,
        callback: EventHandler[RuntimeT],
        *args: JsonValue,
        **kwargs: JsonValue,
    ) -> JsonValue | None:
        event = Event(
            runtime=self.runtime,
            event=self.event,
            args=args,
            kwargs=kwargs,
            callback_name=callback_name,
        )
        self.trace(event)
        value = callback(self.runtime, *args, **kwargs)
        if isinstance(value, ForwardEmit):
            return value.call()
        return value

    def emit(self, *args: JsonValue, **kwargs: JsonValue) -> None:
        for callback_name, callback in self.callbacks.items():
            self._emit_with_tracing(callback_name, callback, *args, **kwargs)

    def call(self, *args: JsonValue, **kwargs: JsonValue) -> JsonValue | None:
        if len(self.callbacks) != 1:
            raise ValueError(
                f"Expected exactly one handler for event, but found {len(self.callbacks)}"
            )
        callback_name, callback = next(iter(self.callbacks.items()))
        return self._call_with_tracing(callback_name, callback, *args, **kwargs)

    def __len__(self) -> int:
        return len(self.callbacks)

    def __call__(self, callback: EventHandler[RuntimeT]) -> EventHandler[RuntimeT]:
        self.do(callback)
        return callback


@define
class Event[RuntimeT: BaseRuntime[Any]]:
    runtime: RuntimeT
    event: Annotated[str, pydantic.StringConstraints(pattern=r"^[a-zA-Z0-9_.-]+$")] = (
        field(validator=validate_via_pydantic())
    )
    args: tuple[JsonValue, ...] = field(factory=tuple)
    kwargs: dict[str, JsonValue] = field(factory=dict)
    callback_name: str | None = field(default=None, repr=False)


def parameters(event: Event[Runtime]) -> dict[str, Any]:
    if event.callback_name is None:
        raise ValueError("Event does not have a callback name for parameter extraction")
    try:
        handler = event.runtime.callbacks[event.event]
    except KeyError:
        raise ValueError(f"No handlers registered for event '{event.event}'") from None

    callback = handler.callbacks.get(event.callback_name)
    if callback is None:
        raise ValueError(
            f"No callback named '{event.callback_name}' found for event '{event.event}'"
        )

    sig = signature(callback)
    out = sig.bind(event.runtime, *event.args, **event.kwargs)
    out.apply_defaults()
    return out.arguments


@define
class Runtime(BaseRuntime["Runtime"]):
    callbacks: dict[str, RuntimeHandlers["Runtime"]] = field(factory=dict)
    tracer: Callable[[Event["Runtime"]], None] | None = None
    state: dict[str, JsonValue] = field(factory=dict, repr=False, init=False)

    def on(self, event: str) -> RuntimeHandlers["Runtime"]:
        if event not in self.callbacks:
            self.callbacks[event] = RuntimeHandlers(self, event)
        return self.callbacks[event]

    def emit(self, event: str, *args: JsonValue, **kwargs: JsonValue) -> None:
        # Here you would implement the logic to emit the event to all registered handlers
        if event in self.callbacks:
            self.callbacks[event].emit(*args, **kwargs)

    def call(
        self, event: str, *args: JsonValue, **kwargs: JsonValue
    ) -> JsonValue | None:
        # Here you would implement the logic to call the event and return the result
        if event in self.callbacks:
            result = self.callbacks[event].call(*args, **kwargs)
            return result
        raise ValueError(f"No handlers registered for event '{event}'")

    def forward_emit(
        self, event: str, *args: JsonValue, **kwargs: JsonValue
    ) -> ForwardEmit["Runtime"]:
        return ForwardEmit(
            event=Event(runtime=self, event=event, args=args, kwargs=kwargs)
        )

    def trace(self, event: Event) -> None:
        if self.tracer:
            self.tracer(event)


@define
class ForwardEmit[RuntimeT: BaseRuntime[Any]]:
    event: Event[RuntimeT]

    def emit(self) -> None:
        self.event.runtime.emit(self.event.event, *self.event.args, **self.event.kwargs)

    def call(self) -> JsonValue | None:
        return self.event.runtime.call(
            self.event.event, *self.event.args, **self.event.kwargs
        )


def create_runtime[R: BaseRuntime[Any]](factory: Callable[[], R] = Runtime) -> R:
    return factory()


def tracer(event: Event[Runtime]) -> None:
    params = parameters(event)
    print(
        f"Tracing event '{event.event}' with callback '{event.callback_name}' and parameters: {params}"
    )


runtime = create_runtime()
runtime.tracer = tracer


@runtime.on("core.print")
def handle_print(runtime: Runtime, message: str, stderr: bool = False) -> None:
    if stderr:
        print(message, file=sys.stderr)
    else:
        print(message)


@runtime.on("core.exit")
def handle_exit(runtime: Runtime, code: int = 0) -> None:
    sys.exit(code)


@runtime.on("core.discovery.events")  # type: ignore
def handle_discovery_events(runtime: Runtime) -> list[str]:
    return list(runtime.callbacks.keys())


@runtime.on("core.startup")
def handle_startup(runtime: Runtime) -> None:
    runtime.emit("core.print", "Runtime started successfully!")
    runtime.emit("core.print", "Emitting startup event to all handlers...")
    print(runtime.call("core.discovery.events"))


@runtime.on("core.startup")
def handle_startup_2(runtime: Runtime) -> ForwardEmit[Runtime]:
    runtime.emit("core.print", "This is another startup handler!")
    return runtime.forward_emit(
        "core.print", "Forwarding emit from second startup handler!"
    )


@runtime.on("example")
def handle_example(runtime: Runtime, data: str) -> ForwardEmit[Runtime]:
    runtime.emit("core.print", f"Received example event with data: {data}")
    return runtime.forward_emit("core.discovery.events")


if __name__ == "__main__":
    runtime.emit("core.startup")
