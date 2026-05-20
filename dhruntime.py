# pyright: standard

from __future__ import annotations

from typing import Callable

from attrs import define, field
from pydantic import JsonValue

Callback = Callable[["Runtime", dict[str, JsonValue]], JsonValue | None]

Auditer = Callable[["AuditerState"], JsonValue | None]


@define
class AuditerState:
    runtime: Runtime
    event_name: str
    callback_name: str
    callback: Callback
    data: dict[str, JsonValue]


@define
class EventCallback:
    runtime: Runtime
    name: str
    callbacks: dict[str, Callback] = field(factory=dict)
    _auditer: Auditer | None = field(init=False, default=None)

    def __attrs_post_init__(self) -> None:
        if self._auditer is None:
            self._auditer = self.runtime.auditer

    def audit(self, auditer: Auditer) -> Auditer:
        self._auditer = auditer
        return auditer

    def _execute_with_audit(
        self, callback_name: str, callback: Callback, data: dict[str, JsonValue]
    ) -> JsonValue | None:
        state = AuditerState(
            runtime=self.runtime,
            event_name=self.name,
            callback_name=callback_name,
            callback=callback,
            data=data,
        )
        auditer = self._auditer or self.runtime.auditer
        if auditer is not None:
            return auditer(state)
        else:
            return callback(self.runtime, data)

    def add_callback(self, callback: Callback, name: str | None = None) -> str:
        if name is None:
            name = callback.__name__
        self.callbacks[name] = callback
        return name

    def remove_callback(self, name: str) -> None:
        self.callbacks.pop(name, None)

    def execute(self, data: dict[str, JsonValue]) -> list[JsonValue | None]:
        return [
            self._execute_with_audit(callback_name, callback, data)
            for callback_name, callback in self.callbacks.items()
        ]

    def call_where_single_callback_only(
        self, data: dict[str, JsonValue]
    ) -> JsonValue | None:
        if len(self.callbacks) == 1:
            callback_name, callback = next(iter(self.callbacks.items()))
            return self._execute_with_audit(callback_name, callback, data)
        else:
            raise RuntimeError(
                f"Event '{self.name}' has {len(self.callbacks)} callbacks, expected exactly 1."
            )

    def __call__(self, callback: Callback) -> Callback:
        return self.callback(callback)

    def callback(self, callback: Callback) -> Callback:
        self.add_callback(callback)
        return callback


@define
class Runtime:
    events: dict[str, EventCallback] = field(factory=dict)
    auditer: Auditer | None = None

    def audit(self, auditer: Auditer) -> Auditer:
        self.auditer = auditer
        return auditer

    def on(self, event: str) -> EventCallback:
        if event not in self.events:
            self.events[event] = EventCallback(runtime=self, name=event)
        return self.events[event]

    def unregister(self, event: str, callback_name: str) -> None:
        if event in self.events:
            self.events[event].remove_callback(callback_name)

    def emit(self, event: str, data: dict[str, JsonValue]) -> None:
        if event in self.events:
            self.events[event].execute(data)

    def call(self, event: str, data: dict[str, JsonValue]) -> JsonValue | None:
        return (
            self.events[event].call_where_single_callback_only(data)
            if event in self.events
            else None
        )


runtime = Runtime()


@runtime.on("success")
def success_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
    print(f"Success callback called with data: {data}")
    return {"status": "success", "received_data": data}


@runtime.on("example_event")
def example_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
    print(f"Received event with data: {data}")
    return runtime.call("success", {"message": "Event processed successfully"})


@runtime.audit
def example_auditer(state: AuditerState) -> JsonValue:
    print(
        f"Auditing event '{state.event_name}' with callback '{state.callback_name}' and data: {state.data}"
    )
    result = state.callback(state.runtime, state.data)
    print(f"Result of callback '{state.callback_name}': {result}")
    return result


if __name__ == "__main__":
    p = runtime.call("example_event", {"key": "value"})
    print(p)
