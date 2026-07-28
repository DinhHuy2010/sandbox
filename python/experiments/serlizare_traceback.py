import traceback
from pprint import pprint
from urllib.parse import quote

import snakemd
from snakemd import Document, Element, Paragraph, new_doc


def a(x):
    return recursion(x)


def recursion(x):
    return a(x + 1)


def te_json(
    te: traceback.TracebackException, *, last_nframes: int | None = None
) -> dict:
    exc_type = te.exc_type
    tp_dict = {
        "name": exc_type.__qualname__,
        "module": exc_type.__module__,
    }
    message = "".join(te.format_exception_only()).strip()
    frames = []
    for frame in te.stack[-last_nframes:] if last_nframes is not None else te.stack:
        frames.append(
            {
                "filename": frame.filename,
                "lineno": frame.lineno,
                "name": frame.name,
                "line": frame.line,
                "locals": frame.locals,
            }
        )
    stack = {"frames": frames, "limit": last_nframes}
    return {
        "type": tp_dict,
        "message": message,
        "stack": stack,
        "context": te_json(te.__context__, last_nframes=last_nframes)
        if te.__context__
        else None,
        "cause": te_json(te.__cause__, last_nframes=last_nframes)
        if te.__cause__
        else None,
        "notes": te.__notes__,
    }


def te_md(te: traceback.TracebackException, *, last_nframes: int | None = None) -> str:
    elements: list[Element] = []
    elements.append(snakemd.Heading("Exception (most recent call last)", level=1))
    for frame in te.stack[-last_nframes:] if last_nframes is not None else te.stack:
        elements.append(
            snakemd.Code(
                f'File "{frame.filename}", line {frame.lineno}, in {frame.name}\n{frame.line}\nLocals: {frame.locals}',
                lang="python",
            )
        )
    search_term = "".join(te.format_exception_only()).strip() + " python"
    elements.append(snakemd.Heading("Exception information", level=2))
    paragraph = Paragraph(f"""
Exception type: {te.exc_type.__module__}.{te.exc_type.__qualname__} (search on Google, Stack Overflow)
""")
    paragraph.insert_link(
        "search on Google",
        f"https://www.google.com/search?q={quote(search_term)}",
    ).insert_link(
        "Stack Overflow",
        f"https://stackoverflow.com/search?q={quote(search_term)}",
    )
    elements.append(paragraph)
    md = Document(elements)
    return str(md)

def te_sexpr(te: traceback.TracebackException, *, last_nframes: int | None = None) -> str:
    frames = []
    for frame in te.stack[-last_nframes:] if last_nframes is not None else te.stack:
        frames.append(
            f'(frame (filename "{frame.filename}") (lineno {frame.lineno}) (name "{frame.name}") (line "{frame.line}") (locals {frame.locals}))'
        )
    exc_type = te.exc_type
    tp_str = f'(type (name "{exc_type.__qualname__}") (module "{exc_type.__module__}"))'
    message = "".join(te.format_exception_only()).strip()
    context = te_sexpr(te.__context__, last_nframes=last_nframes) if te.__context__ else "nil"
    cause = te_sexpr(te.__cause__, last_nframes=last_nframes) if te.__cause__ else "nil"
    notes = f'(notes {" ".join(f'"{note}"' for note in te.__notes__)})' if te.__notes__ else "nil"
    return f'(traceback (type {tp_str}) (message "{message}") (stack ({" ".join(frames)})) (context {context}) (cause {cause}) (notes {notes}))'

try:
    recursion(0)
except Exception as e:
    # print("An exception occurred:")
    # te = traceback.TracebackException.from_exception(e, capture_locals=True)
    # # te.print()
    # for frame in te.stack[-10:]:
    #     print(frame.locals)
    r = te_sexpr(
        traceback.TracebackException.from_exception(e, capture_locals=True),
        last_nframes=10,
    )
    print(r)
