import ast
from inspect import currentframe, getouterframes
from typing import Annotated, Any

import pydantic
from annotated_types import Gt


def cocerce(annotation: Any, value: Any) -> Any:
    return pydantic.TypeAdapter(annotation).validate_python(value)


def lol(val: Any) -> Any:
    frame_info = getouterframes(currentframe())[1]
    frame = frame_info.frame
    frame_locals = frame.f_locals
    frame_globals = frame.f_globals
    p = ast.parse("".join(frame_info.code_context), mode="exec")
    match p.body:
        case [ast.AnnAssign(value=_, annotation=annotation)]:
            annotation = ast.unparse(annotation)
        case [ast.Assign()]:
            return val
        case _:
            raise ValueError("Expected an annotated assignment")
    ann_code = compile(annotation, "<annotation>", "eval")
    try:
        ann = eval(ann_code, frame_globals, frame_locals)
    except Exception:
        ann = Any
    return cocerce(ann, val)


# lol(42)
a: Annotated[int, Gt(0)] = lol("42")
b, c = lol("-1"), lol("hello")
d: pydantic.JsonValue = lol(object())
print(a, b, c)
print(d)
