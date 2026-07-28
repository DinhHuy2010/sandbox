import dis
import linecache
import sys
from inspect import getmodule
from types import FrameType, ModuleType
from typing import Any

import IPython.terminal.embed


def list_print_helper(lst: list[str]) -> str:
    if len(lst) <= 5:
        return ", ".join(lst)
    else:
        items_left = len(lst) - 5
        return ", ".join(lst[:5]) + ", ... ({} more)".format(items_left)


def get_exact_location(frame: FrameType) -> dict[str, Any] | None:
    code = frame.f_code
    f_lasti = frame.f_lasti

    for instr in dis.get_instructions(code):
        if instr.offset == f_lasti:
            return {
                "file": code.co_filename,
                "line": instr.starts_line,
                "column": instr.positions.col_offset if instr.positions else None,
                "end_column": instr.positions.end_col_offset
                if instr.positions
                else None,
                "op": instr.opname,
            }

    return None


def print_frame(frame: FrameType):
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    func_name = frame.f_code.co_name
    pos = get_exact_location(frame)
    line = linecache.getline(filename, lineno)
    print(f"File {filename!r}, line {lineno}, in {func_name}")
    if line:
        print(f"  {line.strip()}")
    if pos:
        start, end = pos["column"], pos["end_column"]
        if start is not None and end is not None:
            arr = [" "] * len(line)
            arr[start:end] = ["^"] * (end - start)
            print("  " + "".join(arr))


def inspect_frame(frame: FrameType):
    print(f"Local variables: {list_print_helper(list(frame.f_locals.keys()))}")
    print(f"Global variables: {list_print_helper(list(frame.f_globals.keys()))}")
    print(f"Built-in variables: {list_print_helper(list(frame.f_builtins.keys()))}")


def load_ipython(frame: FrameType):
    embed_shell = IPython.terminal.embed.InteractiveShellEmbed()
    module = getmodule(frame)
    if module is None:
        module = ModuleType(frame.f_globals.get("__name__", "__main__"))
        module.__dict__.update(frame.f_globals)
    f_locals = frame.f_locals
    embed_shell(
        local_ns=f_locals,
        module=module,
        header=f"""
Entering IPython shell. You can inspect variables and execute code in the current frame's context.
Type 'exit' or 'quit' to leave the IPython shell and return to the tracer
Frame object is: {frame!r}
""",
    )


def tracer(frame: FrameType, event, arg):
    print_frame(frame)
    while True:
        x = input("[C]ontinue/[r]eject/[h]elp? ")
        if x.lower() == "c":
            break
        elif x.lower() == "r":
            print("Execution rejected.")
            sys.exit(1)
        elif x.lower() == "i":
            inspect_frame(frame)
            continue
        elif x.lower() == "ip":
            print("Opening IPython shell...")
            load_ipython(frame)
            continue
        elif x.lower() == "h":
            print("Help:")
            print("  [C]ontinue: Continue execution.")
            print("  [r]eject: Reject execution and exit.")
            print("  [e]xit: Exit the tracer without rejecting execution.")
            print("  [i]nspect: Inspect the current frame.")
            print("  [ip]ython: Open an IPython shell in the current frame.")
            print("  [h]elp: Show this help message.")
        elif x.lower() == "e":
            print("Exiting tracer without rejecting execution.")
            sys.settrace(None)
            return None
        else:
            print("Invalid input. Type 'h' for help.")
    return tracer


def test():
    x = 10
    y = 20
    z = x + y
    print(f"Result: {z}")


if __name__ == "__main__":
    sys.settrace(tracer)
    test()
