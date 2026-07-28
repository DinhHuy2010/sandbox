import sys
from collections import defaultdict
from typing import Counter

call_graph = Counter()
call_stack = []


def func_id(frame):
    code = frame.f_code
    return (code.co_filename, code.co_firstlineno, code.co_name)


def tracer(frame, event, arg):
    global call_stack

    if event == "call":
        callee = func_id(frame)
        caller = call_stack[-1] if call_stack else None

        if caller is not None:
            call_graph[(caller, callee)] += 1

        call_stack.append(callee)
        return tracer

    elif event == "return":
        if call_stack:
            call_stack.pop()
        return tracer

    return tracer


def c():
    pass


def b():
    c()


def a():
    b()
    c()


sys.settrace(tracer)
# a()
from python.lib import smart_cast
smart_cast.cast(int, "10")  # Call the function to generate the call graph
sys.settrace(None)

for (caller, callee), count in call_graph.most_common(5):
    caller_name = f"{caller[2]} ({caller[0]}:{caller[1]})" if caller else "<???>"
    callee_name = f"{callee[2]} ({callee[0]}:{callee[1]})"
    print(f"{caller_name} -> {callee_name}: {count}")
