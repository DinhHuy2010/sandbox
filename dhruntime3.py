# pyright: standard

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, MutableMapping
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Protocol, Self

from attrs import define, field
from pydantic import JsonValue

Callback = Callable[["Runtime", dict[str, JsonValue]], JsonValue | None]

NextMiddleware = Callable[[], JsonValue | None]
Middleware = Callable[["MiddlewareState", NextMiddleware], JsonValue | None]


@define
class MiddlewareState:
    runtime: Runtime
    event_name: str
    callback_name: str
    callback: Callback
    data: dict[str, JsonValue]


@define
class EventCallback:
    runtime: Runtime
    name: str
    callback_name: str | None = field(init=False, default=None)
    callback: Callback | None = field(init=False, default=None)
    _middlewares: list[Middleware] = field(init=False, default=None)
    use_runtime_memory: bool = field(init=False, default=False)

    def __attrs_post_init__(self) -> None:
        if self._middlewares is None:
            self._middlewares = []

    def middleware(self, middleware: Middleware) -> Middleware:
        self._middlewares.append(middleware)
        return middleware

    def _execute_with_middlewares(
        self, callback_name: str, callback: Callback, data: dict[str, JsonValue]
    ) -> JsonValue | None:
        middlewares = self.runtime.middlewares + self._middlewares

        def next_middleware(index: int) -> NextMiddleware:
            if index < len(middlewares):

                def next_func() -> JsonValue | None:
                    return middlewares[index](
                        MiddlewareState(
                            runtime=self.runtime,
                            event_name=self.name,
                            callback_name=callback_name,
                            callback=callback,
                            data=data,
                        ),
                        next_middleware(index + 1),
                    )

                return next_func
            else:

                def final_func() -> JsonValue | None:
                    return callback(self.runtime, data)

                return final_func

        return next_middleware(0)()

    def execute(self, data: dict[str, JsonValue]) -> JsonValue | None:
        if self.callback is None or self.callback_name is None:
            raise ValueError(f"No callback registered for event '{self.name}'")

        with self.runtime.memory.memory_space(use_parent=self.use_runtime_memory):
            result = self._execute_with_middlewares(
                self.callback_name, self.callback, data
            )
        return result

    def set_callback(self, callback: Callback, name: str | None = None) -> None:
        self.callback = callback
        self.callback_name = name or callback.__name__

    def __call__(self, callback: Callback) -> EventCallback:
        self.set_callback(callback)
        return self

    def use_memory(self, *, use_runtime_memory: bool = False) -> Self:
        self.use_runtime_memory = use_runtime_memory
        return self


@define
class SharedMemory(MutableMapping[str, JsonValue]):
    ram_context: ContextVar[dict[str, JsonValue] | None] = field(
        init=False, factory=lambda: ContextVar("ram_context", default=None)
    )

    @contextmanager
    def memory_space(self, *, use_parent: bool = False):
        d = {}
        if use_parent:
            parent_memory = self.ram_context.get()
            if parent_memory is not None:
                d.update(parent_memory)
        token = self.ram_context.set(d)
        try:
            yield self
        finally:
            self.ram_context.reset(token)

    def _get_memory_space(self) -> dict[str, JsonValue]:
        memory_space = self.ram_context.get()
        if memory_space is None:
            raise RuntimeError(
                "No memory space available. Use the 'memory_space' context manager."
            )
        return memory_space

    def __getitem__(self, key: str) -> JsonValue:
        memory_space = self._get_memory_space()
        return memory_space[key]

    def __setitem__(self, key: str, value: JsonValue) -> None:
        memory_space = self._get_memory_space()
        memory_space[key] = value

    def __delitem__(self, key: str) -> None:
        memory_space = self._get_memory_space()
        del memory_space[key]

    def __iter__(self):
        memory_space = self._get_memory_space()
        return iter(memory_space)

    def __len__(self) -> int:
        memory_space = self._get_memory_space()
        return len(memory_space)

    def __repr__(self) -> str:
        try:
            memory_space = self._get_memory_space()
            return f"SharedMemory({memory_space!r})"
        except RuntimeError:
            return "SharedMemory({})"

    def __contains__(self, key: object) -> bool:
        try:
            memory_space = self._get_memory_space()
            return key in memory_space
        except RuntimeError:
            return False

    def clear(self) -> None:
        memory_space = self._get_memory_space()
        memory_space.clear()


class BaseRuntime(ABC):
    @abstractmethod
    def emit(self, event: str, data: dict[str, JsonValue]) -> None:
        pass

    @abstractmethod
    def call(self, event: str, data: dict[str, JsonValue]) -> JsonValue | None:
        pass


class EventDecoratorProtocol(Protocol):
    def __call__(self, callback: Callback) -> Any: ...


class RuntimeWithRegistration[DecoratorT: EventDecoratorProtocol](BaseRuntime):
    @abstractmethod
    def on(self, event: str) -> DecoratorT:
        pass

    @abstractmethod
    def unregister(self, event: str) -> None:
        pass

    def list_registered_events(self) -> list[str]:
        raise NotImplementedError(
            "This class does not support listing registered events."
        )


@define
class Runtime(RuntimeWithRegistration[EventCallback]):
    events: dict[str, EventCallback] = field(factory=dict)
    middlewares: list[Middleware] = field(factory=list)
    _memory: SharedMemory = field(init=False, factory=SharedMemory)

    @property
    def memory(self) -> SharedMemory:
        return self._memory

    def use_middleware(self, middleware: Middleware) -> Middleware:
        self.middlewares.append(middleware)
        return middleware

    def on(self, event: str) -> EventCallback:
        if event not in self.events:
            self.events[event] = EventCallback(runtime=self, name=event)
        return self.events[event]

    def unregister(self, event: str) -> None:
        if event in self.events:
            del self.events[event]

    def emit(self, event: str, data: dict[str, JsonValue]) -> None:
        if event in self.events:
            self.events[event].execute(data)

    def call(self, event: str, data: dict[str, JsonValue]) -> JsonValue | None:
        if event in self.events:
            return self.events[event].execute(data)
        else:
            raise ValueError(f"No callback registered for event '{event}'")

    def async_runtime(self, *, max_workers: int = 4) -> AsyncRuntime:
        return AsyncRuntime(runtime=self, max_workers=max_workers)

    def list_registered_events(self):
        return list(self.events.keys())


@define
class AsyncRuntime:
    runtime: BaseRuntime
    max_workers: int = field(default=4)
    _executor: Executor | None = field(init=False, default=None)

    @property
    def running(self) -> bool:
        return self._executor is not None

    def emit(self, event: str, data: dict[str, JsonValue]) -> Future[None]:
        if self._executor is None:
            raise RuntimeError("AsyncRuntime is not running.")
        return self._executor.submit(self.runtime.emit, event, data)

    def call(self, event: str, data: dict[str, JsonValue]) -> Future[JsonValue | None]:
        if self._executor is None:
            raise RuntimeError("AsyncRuntime is not running.")
        return self._executor.submit(self.runtime.call, event, data)

    def start(self) -> None:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

    def stop(self, *, graceful: bool = True) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=graceful, cancel_futures=not graceful)
            self._executor = None

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop(graceful=exc_type is None)
