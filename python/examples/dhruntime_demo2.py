from python.lib import dhruntime3 as dhruntime

rt = dhruntime.Runtime()


@rt.on("push_event")
def handle_push_event(
    runtime: dhruntime.Runtime, data: dict[str, dhruntime.JsonValue]
) -> dhruntime.JsonValue | None:
    print(f"Received push event with data: {data}")
    return {"status": "success", "message": "Push event handled successfully"}


@handle_push_event.middleware
def log_middleware(
    state: dhruntime.MiddlewareState, next_middleware: dhruntime.NextMiddleware
) -> dhruntime.JsonValue | None:
    print(f"Middleware: Logging event '{state.event_name}' with data: {state.data}")
    result = next_middleware()
    print(f"Middleware: Event '{state.event_name}' processed with result: {result}")
    return result

rt.emit("push_event", {"key": "value"})
