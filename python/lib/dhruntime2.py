# pyright: standard

from __future__ import annotations

from collections.abc import MutableMapping
from concurrent.futures import Executor, Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event
from typing import Callable, Self

from attrs import define, field
from pydantic import JsonValue
from tqdm import tqdm

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

        mem = self.runtime.memory
        if self.use_runtime_memory:
            try:
                runtime_memory = self.runtime.memory._get_memory_space()
            except RuntimeError:
                runtime_memory = {}
        else:
            runtime_memory = {}

        with mem.memory_space():
            mem.update(runtime_memory)
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
    def memory_space(self):
        token = self.ram_context.set({})
        try:
            yield self.ram_context.get()
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


@define
class Runtime:
    events: dict[str, EventCallback] = field(factory=dict)
    middlewares: list[Middleware] = field(factory=list)
    _async_executor: Executor | None = field(init=False, default=None)
    _async_event_loop_running: Event = field(init=False, factory=Event)
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

    def async_emit(self, event: str, data: dict[str, JsonValue]) -> Future[None]:
        if self._async_executor is None:
            raise RuntimeError(
                "Async event loop is not running. Call start_async_event_loop() first."
            )
        return self._async_executor.submit(self.emit, event, data)

    def async_call(
        self, event: str, data: dict[str, JsonValue]
    ) -> Future[JsonValue | None]:
        if self._async_executor is None:
            raise RuntimeError(
                "Async event loop is not running. Call start_async_event_loop() first."
            )
        return self._async_executor.submit(self.call, event, data)

    def start_async_event_loop(self, max_workers: int = 4) -> None:
        if self._async_executor is None:
            self._async_executor = ThreadPoolExecutor(max_workers=max_workers)
            self._async_event_loop_running.set()

    def async_event_loop_running(self) -> bool:
        return self._async_event_loop_running.is_set()

    def stop_async_event_loop(self, *, graceful: bool = True) -> None:
        if self._async_event_loop_running.is_set():
            self._async_event_loop_running.clear()
            if self._async_executor is not None:
                self._async_executor.shutdown(
                    wait=graceful, cancel_futures=not graceful
                )
                self._async_executor = None

    @contextmanager
    def async_event_loop(self, max_workers: int = 4):
        self.start_async_event_loop(max_workers=max_workers)
        try:
            yield
        except Exception:
            self.stop_async_event_loop(graceful=False)
            raise
        finally:
            self.stop_async_event_loop()


if __name__ == "__main__":
    runtime = Runtime()

    @runtime.on("success")
    def success_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
        print(f"Success callback called with data: {data}")
        return {"status": "success", "received_data": data}

    @runtime.on("example_event")
    def example_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
        print(f"Received event with data: {data}")
        return runtime.call("success", {"message": "Event processed successfully"})

    @runtime.use_middleware
    def example_auditer(state: MiddlewareState, next: NextMiddleware) -> JsonValue:
        # print(
        #     f"Auditing event '{state.event_name}' with callback '{state.callback_name}' and data: {state.data}"
        # )
        # result = state.callback(state.runtime, state.data)
        result = next()
        # print(f"Result of callback '{state.callback_name}': {result}")
        return result

    @runtime.use_middleware
    def example_logger(state: MiddlewareState, next: NextMiddleware) -> JsonValue:
        # print(
        #     f"Logging event '{state.event_name}' with callback '{state.callback_name}' and data: {state.data}"
        # )
        result = next()
        # print(f"Result of callback '{state.callback_name}': {result}")
        return result

    @runtime.on("long_time")
    def long_time_callback(runtime: Runtime, data: dict[str, JsonValue]) -> JsonValue:
        import random
        import time

        # print(f"Starting long time processing with data: {data}")
        time.sleep(random.uniform(0, 1))  # Simulate a long processing time
        # print(f"Finished long time processing with data: {data}")
        return {"status": "completed", "received_data": data}

    tasks: list[Future] = []
    with runtime.async_event_loop(50):
        for i in range(500):
            task = runtime.async_call("long_time", {"task_id": i})
            tasks.append(task)
        prog = tqdm(total=len(tasks), desc="Processing tasks", unit="task")
        with prog:
            try:
                while True:
                    done, not_done = wait(tasks, timeout=0.5)
                    prog.update(len(done) - prog.n)  # Update the progress bar
                    if len(not_done) == 0:
                        break
            except KeyboardInterrupt:
                print("Processing interrupted by user.")

    for task in tasks:
        if task.exception() is not None:
            print(f"Task {task} failed with error: {task.exception()}")
        else:
            print(f"Task {task} completed with result: {task.result()}")
