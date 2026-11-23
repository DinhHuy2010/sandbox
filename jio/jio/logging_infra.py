import sys
from contextlib import contextmanager
from threading import Lock
from typing import cast

import structlog


@contextmanager
def get_logger(
    name: str,
    logs_jsonl: str = "logs/general.json",
    include_debug_to_console: bool = False,
):
    lf = open(logs_jsonl, "a", encoding="utf-8")

    js = structlog.processors.JSONRenderer()
    lock = Lock()

    def write_handler(_, __, event_dict):
        with lock:
            lf.write(js(None, None, event_dict) + "\n")
            lf.flush()
        return event_dict

    def drop_console(_, method, event_dict):
        if method == "debug" and not include_debug_to_console:
            raise structlog.DropEvent
        # Drop console output for JSON logs.
        return event_dict

    L = structlog.wrap_logger(
        structlog.PrintLogger(sys.stderr),
        wrapper_class=structlog.make_filtering_bound_logger(0),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            write_handler,
            drop_console,
            structlog.dev.ConsoleRenderer(colors=True, force_colors=True),
        ],
    )
    try:
        yield cast(structlog.typing.FilteringBoundLogger, L.bind(name=name))
    finally:
        lf.close()
