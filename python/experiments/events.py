import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # structlog.dev.ConsoleRenderer(),
        structlog.processors.JSONRenderer(),
    ]
)
logger: structlog.BoundLogger = structlog.get_logger()
logger.info("Event system initialized")
logger.bind(event_system="my_event_system").info("Event system bound to logger")
