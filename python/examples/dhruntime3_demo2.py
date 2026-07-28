from python.lib import dhruntime3

runtime = dhruntime3.Runtime()


@runtime.on("hello-world")
def hello_world(
    runtime: dhruntime3.Runtime, data: dict[str, dhruntime3.JsonValue]
) -> dhruntime3.JsonValue:
    return "Hello, world!"
    # return {"status": "success", "message": "Hello World event processed successfully"}


@runtime.on("stdlib/time/sleep")
def sleep_event(
    runtime: dhruntime3.Runtime, data: dict[str, dhruntime3.JsonValue]
) -> dhruntime3.JsonValue:
    import time

    duration = data.get("duration", 1)
    time.sleep(duration)
    return {"status": "success", "message": f"Slept for {duration} seconds"}


@hello_world.middleware
def log_middleware(
    state: dhruntime3.MiddlewareState, next_middleware: dhruntime3.NextMiddleware
) -> dhruntime3.JsonValue:
    print(f"Middleware: Logging event '{state.event_name}' with data: {state.data}")
    result = next_middleware()
    print(f"Middleware: Event '{state.event_name}' processed with result: {result}")
    return result
