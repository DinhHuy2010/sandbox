from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from enum import Enum
from threading import Condition, Event, RLock
from time import monotonic, sleep
from typing import Callable, Literal

Status = Literal["running", "stopped", "failed"]


class Unit(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self, timeout: float | None = None) -> None: ...

    def restart(self, timeout: float | None = None) -> None:
        self.stop(timeout)
        self.start()

    @abstractmethod
    def status(self) -> Status: ...


class SimpleUnit(Unit):
    """A cooperative background service. Function must accept a stop Event."""

    def __init__(self, function: Callable[..., None], *args: object, **kwargs: object):
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self._lock = RLock()
        self._condition = Condition(self._lock)
        self._stop_event = Event()
        self._state: Status = "stopped"
        self._future: Future[None] | None = None
        self._error: BaseException | None = None
        self._executor: ThreadPoolExecutor | None = None

    def bind(self, executor: ThreadPoolExecutor) -> None:
        with self._lock:
            if self._future is not None and not self._future.done():
                raise RuntimeError("Cannot rebind a running unit")
            self._executor = executor

    def _run(self) -> None:
        try:
            self.function(self._stop_event, *self.args, **self.kwargs)
        except BaseException as exc:
            with self._condition:
                self._error = exc
                self._state = "failed"
                self._condition.notify_all()
            raise
        else:
            with self._condition:
                self._state = "stopped"
                self._condition.notify_all()

    def start(self) -> None:
        with self._condition:
            if self._executor is None:
                raise RuntimeError("Unit must be added to a Manager first")
            if self._future is not None and not self._future.done():
                if self._stop_event.is_set():
                    raise RuntimeError("Unit is still stopping")
                return
            self._stop_event = Event()
            self._error = None
            self._state = "running"
            try:
                self._future = self._executor.submit(self._run)
            except Exception:
                self._state = "failed"
                self._condition.notify_all()
                raise
            self._condition.notify_all()

    def stop(self, timeout: float | None = None) -> None:
        with self._condition:
            future = self._future
            if future is None or future.done():
                return
            self._stop_event.set()
        try:
            future.result(timeout=timeout)
        except TimeoutError:
            raise TimeoutError("Unit did not stop before timeout") from None
        except BaseException:
            # Failure state and original exception are preserved in _run.
            pass

    def status(self) -> Status:
        with self._lock:
            return self._state

    @property
    def error(self) -> BaseException | None:
        with self._lock:
            return self._error

    def wait_for_status(self, expected: Status, timeout: float | None = None) -> bool:
        with self._condition:
            return self._condition.wait_for(lambda: self._state == expected, timeout)


class Manager:
    def __init__(self, max_workers: int = 10):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = RLock()
        self.units: dict[str, SimpleUnit] = {}
        self.dependencies: dict[str, list[tuple[str, Status]]] = {}
        self._closed = False

    def add_unit(
        self,
        name: str,
        unit: SimpleUnit,
        dependencies: list[tuple[str, Status]] | None = None,
    ) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Manager is shut down")
            if name in self.units:
                raise ValueError(f"Duplicate unit: {name}")
            if any(existing is unit for existing in self.units.values()):
                raise ValueError("Unit instance already registered")
            unit.bind(self._executor)
            self.units[name] = unit
            self.dependencies[name] = list(dependencies or [])

    def _order(self, name: str) -> list[str]:
        visited: set[str] = set()
        visiting: set[str] = set()
        ordered: list[str] = []

        def visit(node: str) -> None:
            if node not in self.units:
                raise KeyError(f"Unknown unit: {node}")
            if node in visiting:
                raise ValueError(f"Circular dependency involving {node}")
            if node in visited:
                return
            visiting.add(node)
            for dependency, required in self.dependencies[node]:
                if required == "running":
                    visit(dependency)
                elif dependency not in self.units:
                    raise KeyError(f"Unknown dependency: {dependency}")
            visiting.remove(node)
            visited.add(node)
            ordered.append(node)

        visit(name)
        return ordered

    def start_unit(self, name: str, timeout: float = 30.0) -> None:
        print("[   ] Starting unit:", name)
        deadline = monotonic() + timeout

        with self._lock:
            if self._closed:
                raise RuntimeError("Manager is shut down")
            order = self._order(name)

        for node in order:
            for dep, required in self.dependencies[node]:
                remaining = max(0.0, deadline - monotonic())

                if not self.units[dep].wait_for_status(required, remaining):
                    raise TimeoutError(
                        f"{node}: dependency {dep} did not become {required}"
                    )

            self.units[node].start()
        print("[  OK  ] Started unit:", name)

    def stop_unit(self, name: str, timeout: float = 10.0) -> None:
        print("[   ] Stopping unit:", name)
        with self._lock:
            self.units[name].stop(timeout)
        print("[  OK  ] Stopped unit:", name)

    def restart_unit(self, name: str, timeout: float = 10.0) -> None:
        self.stop_unit(name, timeout)
        self.start_unit(name, timeout)

    def get_unit_status(self, name: str) -> Status:
        with self._lock:
            return self.units[name].status()

    def list_units(self) -> dict[str, Status]:
        with self._lock:
            return {name: unit.status() for name, unit in self.units.items()}

    def shutdown(self, timeout: float = 10.0) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            units = list(self.units.items())
        # Request all stops first, then wait for completion.
        for _, unit in units:
            unit._stop_event.set()
        deadline = monotonic() + timeout
        failures = []
        for name, unit in units:
            try:
                unit.stop(max(0.0, deadline - monotonic()))
            except TimeoutError:
                failures.append(name)
        if failures:
            # Cannot forcibly kill Python threads; do not pretend shutdown succeeded.
            raise TimeoutError(f"Units did not stop: {failures}")
        self._executor.shutdown(wait=True)

    def __enter__(self) -> Manager:
        return self

    def __exit__(self, *exc: object) -> None:
        self.shutdown()


def hello_world(stop: Event) -> None:
    while not stop.wait(1):
        print("Hello, World!")


def goodbye_world(stop: Event) -> None:
    print("Goodbye, World!")


if __name__ == "__main__":
    with Manager() as manager:
        manager.add_unit("hello-world", SimpleUnit(hello_world))
        manager.add_unit(
            "goodbye-world",
            SimpleUnit(goodbye_world),
            dependencies=[("hello-world", "stopped")],
        )
        manager.start_unit("hello-world")
        manager.stop_unit("hello-world")
        manager.start_unit("goodbye-world")
        sleep(3)
        manager.units["goodbye-world"].wait_for_status("stopped", timeout=5)
        print(manager.list_units())
