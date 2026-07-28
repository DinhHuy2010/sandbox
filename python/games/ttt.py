from queue import SimpleQueue
from threading import Event


bus = SimpleQueue()
done = Event()


def send_message(type, **payload):
    message = {"type": type}
    message.update(payload)
    bus.put(message)


def start():
    send_message("start")


def shutdown():
    send_message("exit")


def write_console(message):
    send_message("writeconsole", message=message)


def log(message):
    send_message("log", message=message)


def enter_shell():
    command = input(">>> ")
    if command.strip() == "exit":
        log("Exiting shell...")
        shutdown()
    else:
        # bus.put({"type": "log", "message": f"Executed command: {command}"})
        log(f"Executed command: {command}")
        bus.put({"type": "entershell"})


TYPE_HANDLERS = {
    "start": lambda message: (
        bus.put({"type": "log", "message": "Process started."}),
        bus.put({"type": "entershell"}),
    ),
    "exit": lambda message: done.set(),
    "log": lambda message: print(f"[log] {message['message']}"),
    "writeconsole": lambda message: print(message["message"]),
    "entershell": lambda message: enter_shell(),
}


def main():
    print("Starting the process...")
    while not done.is_set():
        try:
            message = bus.get(timeout=1)
        except Exception:
            continue
        TYPE_HANDLERS.get(message["type"], lambda m: None)(message)


if __name__ == "__main__":
    start()
    main()
