import datetime
import os
from typing import Callable, Literal, Self

from attrs import define, field
import attrs
from pydantic import AwareDatetime, BaseModel, Field, JsonValue


class LogEntry(BaseModel):
    timestamp: AwareDatetime
    event: str
    level: Literal["info", "warning", "error", "debug"] = Field(default="info")
    pid: int
    message: str
    context: dict[str, JsonValue] = Field(default_factory=dict)


class StackTrace(BaseModel):
    filename: str
    line_number: int
    function_name: str
    code_line: str | None = None
    locals: dict[str, str] = Field(default_factory=dict)


class TracebackInfo(BaseModel):
    exception_type: str
    exception_message: str
    stack_trace: list[StackTrace]


class ExceptionLogEntry(LogEntry):
    level: Literal["error"] = Field(default="error")
    traceback: TracebackInfo


def build_traceback_info(exc: BaseException) -> TracebackInfo:
    import traceback

    exception_type = f"{type(exc).__module__}.{type(exc).__qualname__}"
    exception_message = str(exc)
    tb = traceback.TracebackException.from_exception(exc)
    stack_trace = []
    for frame in tb.stack:
        stack_trace.append(
            StackTrace(
                filename=frame.filename,
                line_number=frame.lineno,
                function_name=frame.name,
                code_line=frame.line,
                locals=frame.locals or {},
            )
        )
    return TracebackInfo(
        exception_type=exception_type,
        exception_message=exception_message,
        stack_trace=stack_trace,
    )


def create_entry(
    event: str,
    message: str,
    timestamp: AwareDatetime | None = None,
    pid: int | None = None,
    context: dict[str, JsonValue] | None = None,
) -> LogEntry:
    if context is None:
        context = {}
    if pid is None:
        pid = os.getpid()
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc)
    else:
        timestamp = timestamp.astimezone(datetime.timezone.utc)

    return LogEntry(
        timestamp=timestamp, event=event, pid=pid, message=message, context=context
    )


type Processor = Callable[[LogEntry], LogEntry]
type Publisher = Callable[[LogEntry], None]


def compose_processors(*processors: Processor) -> Processor:
    def composed_processor(entry: LogEntry) -> LogEntry:
        for processor in processors:
            entry = processor(entry)
        return entry

    return composed_processor


@define
class Manager:
    context: dict[str, JsonValue] = field(
        factory=dict, init=False, on_setattr=attrs.setters.frozen
    )
    publishers: list[Publisher] = field(factory=list)
    processors: list[Processor] = field(factory=list)

    def add_processor(self, processor: Processor) -> None:
        self.processors.append(processor)

    def add_publisher(self, publisher: Publisher) -> None:
        self.publishers.append(publisher)

    def bind(self, **context: JsonValue) -> Self:
        new_manager = Manager()
        new_manager.publishers = self.publishers.copy()
        new_manager.processors = self.processors.copy()
        new_manager.context.update({**self.context, **context})
        return new_manager

    def reset(self) -> Self:
        new_manager = Manager()
        new_manager.publishers = self.publishers.copy()
        new_manager.processors = self.processors.copy()
        return new_manager

    def _log(self, entry: LogEntry) -> None:
        if self.context:
            entry.context = {**entry.context, **self.context}
        for processor in self.processors:
            entry = processor(entry)
        for publisher in self.publishers:
            publisher(entry)

    def log(
        self,
        event: str,
        message: str,
        timestamp: AwareDatetime | None = None,
        pid: int | None = None,
        context: dict[str, JsonValue] | None = None,
    ) -> None:
        entry = create_entry(
            event=event, message=message, timestamp=timestamp, pid=pid, context=context
        )
        self._log(entry)

    def log_exception(
        self,
        exc: BaseException,
        event: str = "exception",
        message: str | None = None,
        timestamp: AwareDatetime | None = None,
        pid: int | None = None,
        context: dict[str, JsonValue] | None = None,
    ) -> None:
        if message is None:
            message = f"An exception of type {type(exc).__name__} occurred."
        traceback_info = build_traceback_info(exc)
        entry = ExceptionLogEntry(
            timestamp=timestamp or datetime.datetime.now(datetime.timezone.utc),
            event=event,
            pid=pid or os.getpid(),
            message=message,
            context=context or {},
            traceback=traceback_info,
        )
        self._log(entry)

    def exception(
        self, event: str = "exception", message: str | None = None
    ) -> Callable[[BaseException], None]:
        def log_exception(exc: BaseException) -> None:
            self.log_exception(
                exc=exc,
                event=event,
                message=message,
            )

        return log_exception

    def info(self, event: str, message: str, **kwargs: JsonValue) -> None:
        self.log(event=event, message=message, context=kwargs)

    def warning(self, event: str, message: str, **kwargs: JsonValue) -> None:
        self.log(event=event, message=message, context=kwargs)

    def error(self, event: str, message: str, **kwargs: JsonValue) -> None:
        self.log(event=event, message=message, context=kwargs)

    def debug(self, event: str, message: str, **kwargs: JsonValue) -> None:
        self.log(event=event, message=message, context=kwargs)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_value is not None:
            self.log_exception(exc_value)


def print_logger(entry: LogEntry) -> None:
    print(entry.model_dump_json())


def main() -> None:
    logger = Manager()
    logger.add_publisher(print_logger)
    with logger.bind(user_id=123, session_id="abc"):
        logger.info("user_login", "User logged in successfully")
        try:
            1 / 0
        except ZeroDivisionError as e:
            logger.log_exception(
                e, event="division_error", message="Division by zero occurred"
            )


if __name__ == "__main__":
    main()
