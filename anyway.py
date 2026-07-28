from contextlib import redirect_stdout
from sys import stderr
import sys
import traceback

system_handlers = {}
system_memory = {}
system_stacks = []

PANIC = False


class SystemPanic(RuntimeError):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        self.handlers = system_handlers.copy()
        self.memory = system_memory.copy()

    def __str__(self):
        return f"system panic: {self.code} - {self.message}"


def _panic_normal(sp):
    with redirect_stdout(stderr):
        print(f"System panic: {sp.code} - {sp.message}")
        try:
            raise sp
        except SystemPanic:
            traceback.print_exception(type(sp), sp, sp.__traceback__)
        print("Dumping system state:")
        print("Handlers:")
        for action, handler in sp.handlers.items():
            print(f"  {action}: {handler!r}")
        print("Memory:")
        for key, value in sp.memory.items():
            print(f"  {key}: {value!r}")
    sys.exit(1)


def panic(code, message, from_exception=None):
    sp = SystemPanic(code, message)
    if from_exception:
        sp.__cause__ = from_exception
    if PANIC:
        raise sp
    else:
        _panic_normal(sp)


def guess_number_namespace(domain):
    return f"guess_number:{domain}"


def system_namespace(domain):
    return f"system:{domain}"


def build_request(action, **params):
    return {"action": action, "params": params}


def get_param(request, param_name, default=None):
    return request.get("params", {}).get(param_name, default)


def state_for(system, state_name):
    return system.get(state_name, {})


def register_handler(action, handler):
    system_handlers[action] = handler


def remove_handler(action):
    if action in system_handlers:
        del system_handlers[action]


def system_memory_get(key, default=None):
    return system_memory.get(key, default)


def system_memory_set(key, value):
    system_memory[key] = value


def system_memory_delete(key):
    if key in system_memory:
        del system_memory[key]


def system_stack_push(request):
    system_stacks.append(request)


def system_stack_pop():
    return system_stacks.pop()


def handle_request(request):
    action = request.get("action")
    if action in system_handlers:
        return system_handlers[action](request)
    else:
        raise ValueError(f"No handler registered for action: {action}")


def system_loop():
    while system_stacks:
        request = system_stack_pop()
        try:
            handle_request(request)
        except Exception as e:
            panic("request_handling_error", str(e), e)


def init_game():
    system_memory_set(guess_number_namespace("min_range"), 1)
    system_memory_set(guess_number_namespace("max_range"), 100)
    system_memory_set(guess_number_namespace("number"), None)
    system_memory_set(guess_number_namespace("attempts"), 0)
    system_stack_push(build_request(guess_number_namespace("input")))
    system_stack_push(build_request(guess_number_namespace("get_number")))
    register_handler(guess_number_namespace("input"), guess_number_input_handler)
    register_handler(guess_number_namespace("check"), guess_number_check_handler)
    register_handler(
        guess_number_namespace("get_number"), guess_number_get_number_handler
    )
    register_handler(guess_number_namespace("reset"), guess_number_reset_handler)


def system_start_handler(request):
    print("System is starting...")
    init_game()


def system_exit_handler(request):
    print("System is exiting...")
    sys.exit(0)


def guess_number_get_number_handler(request):
    import random

    min_range = system_memory_get(guess_number_namespace("min_range"), 1)
    max_range = system_memory_get(guess_number_namespace("max_range"), 100)
    number = random.randint(min_range, max_range)
    system_memory_set(guess_number_namespace("number"), number)
    print(
        f"A number has been chosen between {min_range} and {max_range}. Start guessing!"
    )


def guess_number_reset_handler(request):
    system_stack_push(build_request(guess_number_namespace("input")))


def guess_number_input_handler(request):
    guess = int(input("Guess a number between 1 and 100: "))
    system_stack_push(build_request(guess_number_namespace("check"), guess=guess))


def guess_number_check_handler(request):
    guess = get_param(request, "guess")
    number = system_memory_get(guess_number_namespace("number"))
    attempts = system_memory_get(guess_number_namespace("attempts"), 0) + 1
    system_memory_set(guess_number_namespace("attempts"), attempts)

    if number is None:
        print("No number has been generated yet! Please start the game.")
        system_stack_push(build_request(guess_number_namespace("start")))
        return

    if guess < 1 or guess > 100:
        print("Your guess is out of range. Please try again.")
        system_stack_push(build_request(guess_number_namespace("reset")))
    elif guess < number:
        print("Your guess is too low. Try again.")
        system_stack_push(build_request(guess_number_namespace("reset")))
    elif guess > number:
        print("Your guess is too high. Try again.")
        system_stack_push(build_request(guess_number_namespace("reset")))
    else:
        print(
            f"Congratulations! You've guessed the correct number in {attempts} attempts: {guess}"
        )
        system_stack_push(build_request(system_namespace("exit")))


register_handler(system_namespace("start"), system_start_handler)
register_handler(system_namespace("exit"), system_exit_handler)

if __name__ == "__main__":
    system_stack_push(build_request(system_namespace("start")))
    system_loop()
