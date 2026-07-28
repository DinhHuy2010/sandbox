import dhruntime2 as dhruntime

runtime = dhruntime.Runtime()


dispatcher = runtime.on("message")


@dispatcher
def message_callback(
    runtime: dhruntime.Runtime, data: dict[str, dhruntime.JsonValue]
) -> dhruntime.JsonValue:
    print(f"Received message with data: {data}")
    mem = runtime.memory
    mem["last_message"] = data.get("message", "")
    print(f"Updated memory: {mem}")
    return {"status": "received", "received_data": data}


print("Starting runtime...")
with runtime.memory.memory_space():
    runtime.memory["initial_value"] = 42
    o = runtime.call("message", {"message": "Hello, runtime!"})
    print(f"Runtime call returned: {o}")
    print(runtime.memory)
