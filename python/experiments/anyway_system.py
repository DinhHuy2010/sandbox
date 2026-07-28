from abc import ABC, abstractmethod
from enum import Enum
from queue import Empty, Queue
from threading import Event
import threading
from time import sleep
from typing import Any, Callable


class CallStatus(Enum):
    SUCCESS = 1
    FAILURE = 2
    ERROR = 3
    PENDING = 4


def panic(message, cause=None):
    raise RuntimeError(message) from cause


class Container:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class Memory:
    def __init__(self):
        self.ram = {}

    def create_namespace(self, namespace: str):
        if namespace not in self.ram:
            self.ram[namespace] = {}
        return CallStatus.SUCCESS

    def delete_namespace(self, namespace: str):
        if namespace in self.ram:
            del self.ram[namespace]
            return CallStatus.SUCCESS
        return CallStatus.FAILURE

    def assign_data(self, namespace: str, key: str, value: Any):
        self.create_namespace(namespace)
        self.ram[namespace][key] = value
        return CallStatus.SUCCESS

    def retrieve_data(self, namespace: str, key: str, container: Container):
        if namespace in self.ram and key in self.ram[namespace]:
            container.set(self.ram[namespace][key])
            return CallStatus.SUCCESS
        return CallStatus.FAILURE

    def delete_data(self, namespace: str, key: str):
        if namespace in self.ram and key in self.ram[namespace]:
            del self.ram[namespace][key]
            return CallStatus.SUCCESS
        return CallStatus.FAILURE


class Call:
    def __init__(self, func: str, parameters: dict[str, Any]):
        self.func = func
        self.parameters = parameters
        self.status = CallStatus.PENDING
        self.result = None

    def set_result_on_success(self, result: Any):
        self.result = result
        self.status = CallStatus.SUCCESS

    def get_result(self):
        if self.status == CallStatus.SUCCESS:
            return self.result
        else:
            panic(f"Cannot get result: Call status is {self.status.name}")

    def get_result_with_wait(self):
        while self.status == CallStatus.PENDING:
            sleep(0.1)  # Sleep for a short duration to avoid busy waiting
        return self.get_result()


class BaseCallReferenceResolver(ABC):
    @abstractmethod
    def resolve(self, call: Call) -> Callable[..., Any]:
        raise NotImplementedError("Subclasses must implement the resolve method.")


class StandardCallReferenceResolver(BaseCallReferenceResolver):
    def __init__(self):
        self.function_registry = {}

    def register_function(self, name: str, func):
        self.function_registry[name] = func

    def unregister_function(self, name: str):
        if name in self.function_registry:
            del self.function_registry[name]
        else:
            panic(f"Function '{name}' not found in registry.")

    def resolve(self, call: Call):
        if call.func in self.function_registry:
            return self.function_registry[call.func]
        else:
            panic(f"Function '{call.func}' not found in registry.")

    def syscall(self, name: str | None = None):
        def decorator(func):
            if name is None:
                syscall_name = func.__name__
            else:
                syscall_name = name

            def wrapper(**kwargs):
                c = Call(syscall_name, kwargs)
                return c

            self.register_function(syscall_name, func)
            return wrapper

        return decorator


def create_call(func: str, parameters: dict[str, Any]):
    call = Call(func, parameters)
    return call


class System:
    def __init__(self, call_reference_resolver: BaseCallReferenceResolver):
        self.stacks = Queue()
        self.memory = Memory()
        self.call_reference_resolver = call_reference_resolver
        self.system_stop = Event()
        self.system_thread = None

    def push_call(self, call: Call):
        if not isinstance(call, Call):
            panic("Only Call instances can be pushed onto the stack.")
        elif self.system_stop.is_set():
            panic("Cannot push call: system is stopping.")

        self.stacks.put(call)

    def pop_call(self):
        try:
            return self.stacks.get()
        except Empty:
            panic("Call stack is empty.")

    def execute_call(self, call: Call):
        resolved_func = self.call_reference_resolver.resolve(call)
        try:
            result = resolved_func(self, **call.parameters)
            call.set_result_on_success(result)
        except Exception as e:
            call.status = CallStatus.ERROR
            panic(f"Error executing call: {e}", cause=e)

    def run_loop(self):
        while not self.system_stop.is_set():
            call = self.pop_call()
            self.execute_call(call)
            self.stacks.task_done()

    def run(self):
        if self.system_thread is None or not self.system_thread.is_alive():
            self.system_thread = threading.Thread(target=self.run_loop)
            self.system_thread.start()

    def join(self):
        if self.system_thread is not None:
            self.system_thread.join()

    def export_memory(self, namespace: str):
        if namespace in self.memory.ram:
            return self.memory.ram[namespace]
        else:
            panic(f"Namespace '{namespace}' does not exist.")


resolver = StandardCallReferenceResolver()


@resolver.syscall()
def hello_world(system: System):
    print("Hello, world!")


@resolver.syscall()
def add_numbers(system: System, a: int, b: int):
    return a + b


@resolver.syscall()
def multiply_numbers(system: System, a: int, b: int):
    return a * b


@resolver.syscall()
def divide_numbers(system: System, a: int, b: int):
    if b == 0:
        panic("Division by zero is not allowed.")
    return a / b


@resolver.syscall()
def stop_system(system: System):
    system.system_stop.set()
    print("System stopped.")

@resolver.syscall()
def get_random_number(system: System, min_value: int, max_value: int):
    import random
    return random.randint(min_value, max_value)


system = System(resolver)
system.run()
system.push_call(hello_world())
n = add_numbers(a=5, b=3)
system.push_call(n)
print(n.get_result_with_wait())
system.push_call(stop_system())
number = get_random_number(min_value=1, max_value=100)
system.push_call(number)
print(number.get_result_with_wait())
system.join()


