from __future__ import annotations

import operator
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

sys.setrecursionlimit(10**6)  # Increase recursion limit for deep command nesting

# =========================
# AST nodes
# =========================


@dataclass
class MagicRef:
    name: str


@dataclass
class Command:
    path: list[str]
    args: list[Any] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)


# =========================
# Lexer
# =========================

TOKEN_RE = re.compile(
    r"""
    \s*
    (
        /\(                         # nested command start
      | \)                          # close nested command
      | --[A-Za-z_][A-Za-z0-9_.-]* # option/flag
      | <[^<>]+>                    # magic reference
      | "(?:\\.|[^"\\])*"           # quoted string
      | -?\d+\.\d+                  # float
      | -?\d+                       # integer
      | /?[A-Za-z_][A-Za-z0-9_.-]* # command/name/word
      | =                           # assignment
    )
    """,
    re.VERBOSE,
)


def tokenize(source: str) -> list[str]:
    tokens = []
    pos = 0

    while pos < len(source):
        match = TOKEN_RE.match(source, pos)

        if not match:
            if source[pos:].strip() == "":
                break

            raise SyntaxError(
                f"Unexpected character at position {pos}: {source[pos : pos + 20]!r}"
            )

        tokens.append(match.group(1))
        pos = match.end()

    return tokens


# =========================
# Parser
# =========================


class Parser:
    def __init__(self, source: str):
        self.tokens = tokenize(source)
        self.pos = 0

    def peek(self) -> str | None:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def consume(self, expected: str | None = None) -> str:
        token = self.peek()

        if token is None:
            raise SyntaxError("Unexpected end of input")

        if expected is not None and token != expected:
            raise SyntaxError(f"Expected {expected!r}, got {token!r}")

        self.pos += 1
        return token

    def parse(self) -> Command:
        command = self.parse_command(top_level=True)

        if self.peek() is not None:
            raise SyntaxError(f"Unexpected token after command: {self.peek()!r}")

        return command

    def parse_command(self, top_level: bool = False) -> Command:
        first = self.consume()

        if top_level:
            if not first.startswith("/") or first == "/(":
                raise SyntaxError("Top-level command must start with '/'")

            first = first[1:]

        path = [first]

        # Treat ordinary words immediately following the command
        # as command-path components until a real value/option begins.
        #
        # Example:
        # /variable set "hello" "world"
        #
        # becomes path=["variable", "set"]
        while self.peek() is not None:
            token = self.peek()

            if self._starts_value(token) or token.startswith("--") or token == ")":
                break

            path.append(self.consume())

        args = []
        options = {}

        while self.peek() is not None and self.peek() != ")":
            token = self.peek()

            if token.startswith("--"):
                name, value = self.parse_option()
                options[name] = value
            else:
                args.append(self.parse_value())

        return Command(
            path=path,
            args=args,
            options=options,
        )

    def parse_option(self) -> tuple[str, Any]:
        token = self.consume()

        name = token[2:]

        # --immutable
        if self.peek() != "=":
            return name, True

        # --expire=3600
        self.consume("=")
        value = self.parse_value()

        return name, value

    def parse_value(self) -> Any:
        token = self.peek()

        if token is None:
            raise SyntaxError("Expected a value")

        # Nested command: /(...)
        if token == "/(":
            self.consume("/(")

            command = self.parse_command(top_level=False)

            self.consume(")")

            return command

        # Magic reference: <response.latest>
        if token.startswith("<") and token.endswith(">"):
            self.consume()
            return MagicRef(token[1:-1])

        # String
        if token.startswith('"'):
            self.consume()
            return self._decode_string(token)

        # Float
        if re.fullmatch(r"-?\d+\.\d+", token):
            self.consume()
            return float(token)

        # Integer
        if re.fullmatch(r"-?\d+", token):
            self.consume()
            return int(token)

        raise SyntaxError(f"Expected value, got {token!r}")

    @staticmethod
    def _starts_value(token: str) -> bool:
        return (
            token == "/("
            or token.startswith(('"', "<"))
            or bool(re.fullmatch(r"-?\d+(?:\.\d+)?", token))
        )

    @staticmethod
    def _decode_string(token: str) -> str:
        # Strip quotes and process basic Python-style escapes.
        raw = token[1:-1]
        return bytes(raw, "utf-8").decode("unicode_escape")


class Interpreter:
    def __init__(self):
        self.states = {}
        self.add_state("call_stack", [])
        self.add_command(["define"], self.define_command)
        self.add_command(["help"], self._help)

    def add_state(self, name: str, value: Any):
        self.states[name] = value

    def get_state(self, name: str) -> Any:
        return self.states[name]

    def delete_state(self, name: str):
        if name in self.states:
            del self.states[name]

    def add_command(self, path: list[str], func):
        # Placeholder for adding a command to the interpreter.
        # In a real implementation, this would store the command path and associated function.
        self.add_state(f"commands.{'.'.join(path)}", func)

    def remove_command(self, path: list[str]):
        # Placeholder for removing a command from the interpreter.
        # In a real implementation, this would remove the command path and associated function.
        self.delete_state(f"commands.{'.'.join(path)}")

    def add_magic_ref(self, name: str, func):
        # Placeholder for adding a magic reference to the interpreter.
        # In a real implementation, this would store the magic reference name and associated function.
        self.add_state(f"magic_refs.{name}", func)

    def remove_magic_ref(self, name: str):
        # Placeholder for removing a magic reference from the interpreter.
        # In a real implementation, this would remove the magic reference name and associated function.
        self.delete_state(f"magic_refs.{name}")

    def set_option(self, name: str, value: Any):
        self.add_state(f"options.{name}", value)

    def get_option(self, name: str, default: Any = None) -> Any:
        key = f"options.{name}"
        return self.get_state(key) if key in self.states else default

    def remove_option(self, name: str):
        self.delete_state(f"options.{name}")

    def set_last_response(self, response: Any):
        self.add_state("last_response", response)

    def push_call_stack(self, frame):
        self.get_state("call_stack").append(frame)

    def pop_call_stack(self):
        if self.get_state("call_stack"):
            return self.get_state("call_stack").pop()
        return None

    def resolve_scoped_name(self, name: str):
        # Placeholder for argument resolution logic.
        # In a real implementation, this would look up the argument name in the current context.
        stack = self.get_state("call_stack")
        if not stack:
            raise ValueError(f"Scoped name '{name}' not found in call stack")
        for frame in reversed(stack):
            if name in frame:
                return frame[name]
        raise ValueError(f"Scoped name '{name}' not found in call stack")

    def define_command(self, interpreter: Interpreter, name: str, *spec, **options):
        name = interpreter.evaluate_value(name)
        *params, func = spec

        def user_defined(interpreter: Interpreter, *call_args, **call_options):
            if len(call_args) != len(params):
                raise ValueError(
                    f"Expected {len(params)} arguments, got {len(call_args)}"
                )

            frame = dict(
                zip(
                    (f"params.{p}" for p in params),
                    (interpreter.evaluate_value(arg) for arg in call_args),
                )
            )
            interpreter.push_call_stack(frame)

            try:
                result = interpreter.evaluate(func)
            finally:
                interpreter.pop_call_stack()

            return result

        path = self.evaluate_value(name).split(":")

        self.add_command(path, user_defined)
        return {
            "type": "done",
            "message": f"User-defined command '{' '.join(path)}' registered, use /{' '.join(path)} to invoke it.",
        }

    def evaluate(self, command: Command | MagicRef | Any) -> Any:
        if isinstance(command, MagicRef):
            if command.name.startswith(("params.", "local.")):
                param_name = command.name
                return {"type": "value", "value": self.resolve_scoped_name(param_name)}

            return self.get_state(f"magic_refs.{command.name}")(self)

        elif isinstance(command, Command):
            # Evaluate arguments
            evaluated_args = [arg for arg in command.args]

            # Evaluate options
            evaluated_options = {name: value for name, value in command.options.items()}

            # Execute the command
            o = self.execute(Command(command.path, evaluated_args, evaluated_options))
            return o
        return {"type": "value", "value": command}

    def _help(self, *args, **options):
        def generator():
            yield {"type": "echo", "value": "Available commands:"}
            for key in self.states:
                if key.startswith("commands."):
                    command_path = key[len("commands.") :]
                    command = " ".join(command_path.split("."))
                    yield {"type": "echo", "value": f"  /{command}"}
            yield {"type": "done", "message": "End of help."}

        return {
            "type": "stream",
            "iterable": generator(),
        }

    def evaluate_value(self, value: Any) -> Any:
        out = self.evaluate(value)
        if out["type"] != "value":
            raise ValueError(f"Expected a value, got {out['type']}")
        return out["value"]

    def _execute(self, command: Command) -> Any:
        # Placeholder for command execution logic.
        # In a real implementation, this would look up the command path
        # and execute the corresponding function with the provided args and options.
        command_key = f"commands.{'.'.join(command.path)}"
        if command_key not in self.states:
            raise ValueError(f"Command not found: {' '.join(command.path)}")
        func = self.get_state(command_key)
        return func(self, *command.args, **command.options)

    def execute(self, command: Command) -> Any:
        result = self._execute(command)
        self.set_last_response(result)
        return result


def set_variable(interpreter: Interpreter, name: str, value: Any, **options):
    name = interpreter.evaluate_value(name)
    value = interpreter.evaluate_value(value)
    interpreter.add_state(f"variables.{name}", value)
    return {
        "type": "done",
        "message": f"Variable '{name}' set to '{value}'",
    }


def get_variable(interpreter: Interpreter, name: str) -> Any:
    name = interpreter.evaluate_value(name)
    return {
        "type": "value",
        "value": interpreter.get_state(f"variables.{name}"),
    }


def echo(interpreter: Interpreter, *messages: Any, **options):
    return {
        "type": "echo",
        "value": (
            options.get("separator", " ").join(
                str(interpreter.evaluate_value(message)) for message in messages
            )
        ),
    }


def ack(interpreter: Interpreter, message: Any, **options):
    return {
        "type": "ack",
        "message": interpreter.evaluate_value(message),
    }


def multiply(interpreter: Interpreter, a: float, b: float, **options):
    return {
        "type": "value",
        "value": interpreter.evaluate_value(a) * interpreter.evaluate_value(b),
    }


def subtract(interpreter: Interpreter, a: float, b: float, **options):
    return {
        "type": "value",
        "value": interpreter.evaluate_value(a) - interpreter.evaluate_value(b),
    }


def add(interpreter: Interpreter, a: float, b: float, **options):
    return {
        "type": "value",
        "value": interpreter.evaluate_value(a) + interpreter.evaluate_value(b),
    }


def countdown(interpreter: Interpreter, start: int, **options):
    start = interpreter.evaluate_value(start)

    def generator():
        for i in range(start, 0, -1):
            yield {"type": "echo", "value": f"Countdown: {i}"}
        yield {"type": "done", "message": "Countdown complete!"}

    return {
        "type": "stream",
        "iterable": generator(),
    }


def fail(interpreter: Interpreter, message: Any, **options):
    return {
        "type": "error",
        "message": interpreter.evaluate_value(message),
    }


def whatif(
    interpreter: Interpreter,
    condition: Any,
    if_true: Any,
    if_false: Any = None,
    **options,
):
    condition_value = interpreter.evaluate_value(condition)
    if condition_value:
        return interpreter.evaluate(if_true)
    else:
        return interpreter.evaluate(if_false)


def array_create(interpreter, *values, **options):
    return {
        "type": "value",
        "value": [interpreter.evaluate_value(v) for v in values],
    }


def array_get(interpreter, array, index, **options):
    array = interpreter.evaluate_value(array)
    index = interpreter.evaluate_value(index)

    return {
        "type": "value",
        "value": array[index],
    }


def array_length(interpreter, array, **options):
    array = interpreter.evaluate_value(array)

    return {
        "type": "value",
        "value": len(array),
    }


def dict_create(interpreter, *items, **options):
    if len(items) % 2 != 0:
        raise ValueError("dict create expects key/value pairs")

    result = {}

    for i in range(0, len(items), 2):
        key = interpreter.evaluate_value(items[i])
        value = interpreter.evaluate_value(items[i + 1])
        result[key] = value

    return {
        "type": "value",
        "value": result,
    }


def dict_get(interpreter, mapping, key, **options):
    mapping = interpreter.evaluate_value(mapping)
    key = interpreter.evaluate_value(key)

    return {
        "type": "value",
        "value": mapping[key],
    }


def array_append(interpreter, array, value, **options):
    array = interpreter.evaluate_value(array)
    value = interpreter.evaluate_value(value)

    return {
        "type": "value",
        "value": [*array, value],
    }


def dict_set(interpreter, mapping, key, value, **options):
    mapping = interpreter.evaluate_value(mapping)
    key = interpreter.evaluate_value(key)
    value = interpreter.evaluate_value(value)

    return {
        "type": "value",
        "value": {
            **mapping,
            key: value,
        },
    }


CMPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
}


def _factory_compare(op):
    def compare(interpreter: Interpreter, a: Any, b: Any, **options):
        a_value = interpreter.evaluate_value(a)
        b_value = interpreter.evaluate_value(b)
        return {
            "type": "value",
            "value": op(a_value, b_value),
        }

    return compare


def let(interpreter: Interpreter, name, value, body, **options):
    name = interpreter.evaluate_value(name)
    value = interpreter.evaluate_value(value)

    frame = {f"local.{name}": value}
    interpreter.push_call_stack(frame)

    try:
        return interpreter.evaluate(body)
    finally:
        interpreter.pop_call_stack()


def dict_has(interpreter: Interpreter, mapping, key, **options):
    mapping = interpreter.evaluate_value(mapping)
    key = interpreter.evaluate_value(key)

    return {
        "type": "value",
        "value": key in mapping,
    }


def register_default_commands(interpreter: Interpreter):
    interpreter.add_command(["variable", "set"], set_variable)
    interpreter.add_command(["variable", "get"], get_variable)
    interpreter.add_command(["echo"], echo)
    interpreter.add_command(["ack"], ack)
    interpreter.add_command(["math", "multiply"], multiply)
    interpreter.add_command(["math", "add"], add)
    interpreter.add_command(["math", "subtract"], subtract)
    interpreter.add_magic_ref(
        "response.latest", lambda interp: interp.get_state("last_response")
    )
    interpreter.add_command(["fail"], fail)
    interpreter.add_magic_ref("true", lambda interp: {"type": "value", "value": True})
    interpreter.add_magic_ref("false", lambda interp: {"type": "value", "value": False})
    interpreter.add_command(["whatif"], whatif)
    for key, op in CMPS.items():
        interpreter.add_command(["compare", key], _factory_compare(op))
    interpreter.add_command(["clear"], lambda interp, **options: {"type": "clear"})
    array_register(interpreter)
    dict_register(interpreter)
    interpreter.add_command(["do"], do)
    interpreter.add_command(["let"], let)


def array_register(interpreter: Interpreter):
    interpreter.add_command(["array", "create"], array_create)
    interpreter.add_command(["array", "get"], array_get)
    interpreter.add_command(["array", "length"], array_length)
    interpreter.add_command(["array", "append"], array_append)


def dict_register(interpreter: Interpreter):
    interpreter.add_command(["dict", "create"], dict_create)
    interpreter.add_command(["dict", "get"], dict_get)
    interpreter.add_command(["dict", "set"], dict_set)
    interpreter.add_command(["dict", "has"], dict_has)


def do(interpreter: Interpreter, *expressions, **options):
    result = {"type": "value", "value": None}

    for expr in expressions:
        result = interpreter.evaluate(expr)

    return result


def execute_script(
    lines: list[str], *, interpreter: Interpreter | None = None
) -> list[Any]:
    def handler(result, nested=False):
        if result["type"] not in {"stream", "clear"}:
            print("< ", end="")
        if result["type"] == "done":
            print(result["message"])
        elif result["type"] == "value":
            print(f"Result: {result['value']}")
        elif result["type"] == "stream":
            iterable = result["iterable"]
            for item in iterable:
                handler(item, nested=True)
        elif result["type"] == "echo":
            print(result["value"])
        elif result["type"] == "ack":
            print("ack:", result["message"])
        elif result["type"] == "error":
            print(f"Error: {result['message']}")
        elif result["type"] == "clear":
            subprocess.call("clear" if os.name == "posix" else "cls", shell=True)
        else:
            raise ValueError(f"Unknown result type: {result['type']}")

    if interpreter is None:
        interpreter = Interpreter()
        register_default_commands(interpreter)

    verbose = interpreter.get_option("verbose")

    for line in lines:
        if verbose:
            print(f"> {line}")

        parser = Parser(line)
        command = parser.parse()
        result = interpreter.execute(command)
        handler(result)


# =========================
# Demo
# =========================


def accept_any_args(interpreter: Interpreter, *args, **options):
    return {
        "type": "ack",
        "message": f"Accepted args: {args}, options: {options}",
    }


def interactive():
    from prompt_toolkit import PromptSession

    interpreter = Interpreter()
    register_default_commands(interpreter)
    interpreter.add_command(["countdown"], countdown)
    interpreter.set_option("verbose", True)
    interpreter.add_command(["any", "args"], accept_any_args)

    examples = [
        '/variable set "hello" "world" --immutable --expire=3600',
        '/echo /(variable get "hello")',
        "/math multiply /(math add 2 3) 4",
        "/echo <response.latest>",
        '/ack "Hello"',
        "/countdown 5",
        '/fail "This is an error message"',
        "/echo <true>",
        '/any args 1 2 3 --option1="value1" --option2="value2" --option3 --explict-bool-option4=<true> --explict-bool-option5=<false> --with-command-eval=/(math add 10 20)',
        # '/echo --option=/(variable get "hello")',
        '/whatif /(compare eq /(variable get "hello") "world") /(echo "Condition is true") "False string"',
        """/define "fib" "n" /(whatif /(compare le <params.n> 1) <params.n> /(math add /(fib /(math subtract <params.n> 1)) /(fib /(math subtract <params.n> 2))))""",
    ]
    execute_script(examples, interpreter=interpreter)
    session = PromptSession()
    while True:
        try:
            line = session.prompt("> ")
            if line:
                execute_script([line], interpreter=interpreter)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the interactive command interpreter."
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Path to a script file to execute before starting the interactive session.",
    )
    args = parser.parse_args()
    if args.file:
        if not os.path.isfile(args.file):
            print(f"Error: File '{args.file}' does not exist.")
        else:
            with open(args.file, "r") as f:
                lines = f.readlines()
            execute_script(lines)
    else:
        interactive()
