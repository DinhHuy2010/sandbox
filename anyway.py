from abc import ABC, abstractmethod
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Event, Lock
from time import sleep
from typing import Literal

Status = Literal["running", "stopped", "failed"]


class Unit(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    def restart(self) -> None:
        if self.status() == "running":
            self.stop()
        self.start()

    @abstractmethod
    def status(self) -> Status: ...


class SimpleUnit(Unit):
    def __init__(
        self,
        function: Callable[[Event], None],
        executor: ThreadPoolExecutor,
    ):
        self.function = function
        self.executor = executor
        self.stop_event = Event()
        self._status: Status = "stopped"
        self._future: Future | None = None
        self._lock = Lock()

    def _run(self) -> None:
        try:
            self.function(self.stop_event)
        except Exception:
            with self._lock:
                self._status = "failed"
            raise
        else:
            with self._lock:
                self._status = "stopped"

    def start(self) -> None:
        with self._lock:
            if self._status == "running":
                return

            if self._future and not self._future.done():
                return

            self.stop_event.clear()
            self._status = "running"
            try:
                self._future = self.executor.submit(self._run)
            except Exception:
                self._status = "failed"
                raise

    def stop(self) -> None:
        with self._lock:
            if self._status == "running":
                self.stop_event.set()

    def status(self) -> Status:
        with self._lock:
            return self._status


class AdvancedUnit(SimpleUnit):
    def __init__(
        self,
        function: Callable[[Event], None],
        executor: ThreadPoolExecutor,
        manager: "UnitManager",
        dependencies: list[tuple[str, str]],
    ):
        super().__init__(function, executor)
        self.manager = manager
        self.dependencies = dependencies

    def start(self) -> None:
        self._wait_deps()
        super().start()

    def _wait_deps(self):
        while True:
            print("[] Waiting for dependencies to be met...")
            all_deps_met = True
            for dep_name, required_status in self.dependencies:
                dep_unit = self.manager.units.get(dep_name)
                if not dep_unit or dep_unit.status() != required_status:
                    all_deps_met = False
                    break
            if all_deps_met:
                print("[ ok ] All dependencies met.")
                break
            sleep(1)

    def stop(self) -> None:
        super().stop()
        for dep_name, _ in self.dependencies:
            dep_unit = self.manager.units.get(dep_name)
            if dep_unit and dep_unit.status() == "running":
                dep_unit.stop()


class UnitManager:
    def __init__(self):
        self.units: dict[str, Unit] = {}

    def add_unit(self, name: str, unit: Unit) -> None:
        self.units[name] = unit

    def start_all(self) -> None:
        for unit in self.units.values():
            unit.start()

    def stop_all(self) -> None:
        for unit in self.units.values():
            unit.stop()

    def start(self, name: str) -> None:
        unit = self.units.get(name)
        if unit:
            unit.start()

    def stop(self, name: str) -> None:
        unit = self.units.get(name)
        if unit:
            unit.stop()

    def status(self, name: str) -> Status | None:
        unit = self.units.get(name)
        if unit:
            return unit.status()
        return None

    def restart(self, name: str) -> None:
        unit = self.units.get(name)
        if unit:
            unit.restart()

    def status_all(self) -> dict[str, Status]:
        return {name: unit.status() for name, unit in self.units.items()}


def hello_world(stop_event: Event) -> None:
    while not stop_event.is_set():
        print("Hello, World!")
        stop_event.wait(1)


def goodbye_world(stop_event: Event) -> None:
    while not stop_event.is_set():
        print("Goodbye, World!")
        stop_event.wait(1)


manager = UnitManager()
manager.add_unit(
    "hello_world", SimpleUnit(hello_world, ThreadPoolExecutor(max_workers=1))
)
manager.add_unit(
    "goodbye_world", AdvancedUnit(goodbye_world, ThreadPoolExecutor(max_workers=1), manager, [("hello_world", "started")])
)
manager.start("hello_world")  # This will start the hello_world unit
manager.start("goodbye_world")  # This will raise an error because hello_world is not stopped

