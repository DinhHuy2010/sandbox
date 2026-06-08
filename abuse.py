import itertools
import threading
import time
from collections import deque
from contextlib import contextmanager
from time import sleep
from typing import Any, Callable

# Thread-safe event queue using deque
stacks: deque[tuple[int, str, Any]] = deque()
handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
results: dict[int, Any] = {}

# Thread-safe atomic counter for unique Session IDs
sid_counter = itertools.count(1)


def send(event, data):
    sid = next(sid_counter)
    stacks.append((sid, event, data))  # Thread-safe append
    return sid


def register_handler(event, handler):
    handlers[event] = handler


def for_event(event):
    def decorator(func):
        register_handler(event, func)
        return func

    return decorator


def is_complete(sid):
    return sid in results


def get_result(sid):
    if sid not in results:
        raise ValueError(f"Result for sid {sid} not available")
    out = results[sid]
    if exc := out.get("error"):
        raise exc
    return out["result"]


def wait(sid, interval=0.1, timeout=None):

    start_time = time.time()
    while not is_complete(sid):
        if timeout is not None and (time.time() - start_time) > timeout:
            raise TimeoutError(f"Timeout waiting for sid {sid}")
        sleep(interval)
    return get_result(sid)


def wait_multiple(*sids, interval=0.1, timeout=None):
    start_time = time.time()
    while not all(is_complete(sid) for sid in sids):
        if timeout is not None and (time.time() - start_time) > timeout:
            raise TimeoutError(f"Timeout waiting for sids {sids}")
        sleep(interval)
    return [get_result(sid) for sid in sids]


def event_loop():
    # Process everything currently in the queue
    while True:
        try:
            sid, event, data = stacks.popleft()  # O(1) thread-safe pop from left
        except IndexError:
            break  # Queue is empty

        print(f"Processing event {event} with data {data} (sid: {sid})")
        if event in handlers:
            try:
                value = handlers[event](data)
            except Exception as e:
                results[sid] = {"error": e}
            else:
                results[sid] = {"result": value}
        else:
            print(f"No handler registered for event {event}")


_event_loop_signal: threading.Event | None = None


def start_event_loop():
    global _event_loop_signal
    if _event_loop_signal is not None:
        raise RuntimeError("Event loop already running")

    signal = threading.Event()

    def run():
        while not signal.is_set():
            event_loop()
            sleep(0.1)

    p = threading.Thread(target=run, daemon=True)  # Good practice to make this a daemon
    p.start()
    _event_loop_signal = signal
    return signal


def stop_event_loop():
    global _event_loop_signal
    if _event_loop_signal is None:
        raise RuntimeError("Event loop not running")
    _event_loop_signal.set()
    _event_loop_signal = None


@contextmanager
def loop_ctx():
    start_event_loop()
    try:
        yield
    finally:
        stop_event_loop()


# --- Decorators and Mock Tasks ---


@for_event("event1")
def handle_event1(data):
    print(f"Handling event1 with data: {data}")
    return "result1"


@for_event("event2")
def handle_event2(data):
    print(f"Handling event2 with data: {data}")
    return "result2"


def call_event1():
    sid = send("event1", {"key": "value1"})
    print(f"Sent event1 with sid {sid}")
    return sid


def call_event2():
    sid = send("event2", {"key": "value2"})
    print(f"Sent event2 with sid {sid}")
    return sid


if __name__ == "__main__":
    with loop_ctx():
        val1, val2 = wait_multiple(call_event1(), call_event2())
        print(f"Received results: {val1}, {val2}")
