import dhruntime3 as dhruntime

runtime = dhruntime.Runtime()


dispatcher = runtime.on("message").use_memory(use_runtime_memory=True)


@dispatcher
def message_callback(
    runtime: dhruntime.Runtime, data: dict[str, dhruntime.JsonValue]
) -> dhruntime.JsonValue:
    print(f"Received message with data: {data}")
    mem = runtime.memory
    mem["last_message"] = data.get("message", "")
    print(f"Updated memory: {mem}")
    return {"status": "received", "received_data": data}


@dispatcher.middleware
def logging_middleware(
    state: dhruntime.MiddlewareState,
    next: dhruntime.NextMiddleware,
) -> dhruntime.JsonValue:
    print(
        f"Logging middleware: Before calling the next function with data: {state.data}"
    )
    result = next()
    print(f"Logging middleware: After calling the next function. Result: {result}")
    return result


print("Starting runtime...")
with runtime.memory.memory_space():
    runtime.memory["initial_value"] = 42
    with runtime.memory.memory_space(use_parent=True):
        runtime.memory["nested_value"] = 100
        print(f"Nested memory: {runtime.memory}")
    o = runtime.call("message", {"message": "Hello, runtime!"})
    print(f"Runtime call returned: {o}")
    print(runtime.memory)
