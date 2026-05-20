import sys

balance = 1000000.0


def charge(amount):
    global balance
    balance -= amount
    if balance <= 0:
        print("❌ Out of credits. Execution terminated.")
        sys.settrace(None)
        sys.exit(1)
    # print(f"💸 Charged {amount:.2f}, remaining: {balance:.2f}")


def tracer(frame, event, arg):
    module = frame.f_globals.get("__name__", "__main__")
    if module in {"importlib._bootstrap", "importlib._bootstrap_external"}:
        return tracer

    # print_frame(frame)
    if event == "call":
        if module == "__main__":
            charge(0.5)
        else:
            charge(1.0)

    elif event == "line" and module == "__main__":
        charge(0.1)

    return tracer


def abc(a, b):
    import random

    if random.random() < 0.1:
        pass
    return a + b


if __name__ == "__main__":
    import IPython

    sys.settrace(tracer)

    IPython.embed()
    sys.settrace(None)
