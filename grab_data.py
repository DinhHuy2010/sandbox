from collections import UserDict, deque
from pprint import pprint


context = {}


def go(path):
    if path == "init":
        print("Welcome to number guessing game!")
        context["number.winning"] = 42
        context["game.state"] = "playing"
        context["game.attempts"] = 0
        return "continue:guess"
    elif path == "exit":
        print("Goodbye!")
        return "ack:ok"
    elif path == "guess":
        guess = int(input("Enter your guess: "))
        if guess == context["number.winning"]:
            print("Congratulations! You guessed the correct number.")
            return "ack:ok"
        elif guess < context["number.winning"]:
            print("Too low! Try again.")
            context["game.attempts"] += 1
            return "continue:guess"
        elif guess > context["number.winning"]:
            print("Too high! Try again.")
            context["game.attempts"] += 1
            return "continue:guess"


def runtime(handler, init):
    path = init
    trace = [("<runtime>", f"continue:{init}")]
    while True:
        try:
            result = handler(path)
        except KeyboardInterrupt:
            result = "ack:interrupt"
        except Exception as e:
            result = f"ack:error_{e.__class__.__name__}"
        restype, value = result.split(":", 1)
        trace.append((path, result))
        if restype == "continue":
            path = value
        elif restype == "ack" and value == "ok":
            break
        else:
            print("Unknown response:", result)
            print("Context dump:")
            pprint(context)
            print("Trace dump:")
            for p, r in trace:
                print(f"  {p} -> {r}")
            break


def runtime2(handler, dump_history=False):
    trace = deque([("<runtime>", "init")])
    history = []

    while trace:
        source, action = trace.popleft()

        for item in handler(action):
            if isinstance(item, str):
                next_action = item
                next_source = action

            elif isinstance(item, tuple):
                next_action = item[0]
                next_source = item[1] if len(item) > 1 else action

            else:
                raise TypeError(f"Invalid item from handler: {item}")

            history.append((next_source, next_action))

            if next_action == "<halt>":
                if dump_history:
                    print("History dump:")
                    for p, r in history:
                        print(f"  {p} -> {r}")
                return history

            trace.append((next_source, next_action))

    if dump_history:
        print("History dump:")
        for p, r in history:
            print(f"  {p} -> {r}")

    return history


def example(action):
    if action == "init":
        print("Welcome to the example handler!")
        yield "ask_name"
        yield "ask_age"
        yield "ask_continue"
    elif action == "ask_name":
        name = input("What is your name? ")
        print(f"Hello, {name}!")
    elif action == "ask_age":
        age = input("How old are you? ")
        print(f"You are {age} years old.")
    elif action == "ask_continue":
        cont = input("Do you want to continue? (yes/no) ")
        if cont.lower() == "yes":
            yield "ask_name"
            yield "ask_age"
            yield "ask_continue"
        else:
            yield "<halt>"


runtime2(example, dump_history=True)
# if __name__ == "__main__":
#     runtime(go, "init")
