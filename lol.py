import sys
import json_stream


def visit(value, path):
    if isinstance(value, str):
        print(value)


json_stream.visit(sys.stdin.buffer, visit)
