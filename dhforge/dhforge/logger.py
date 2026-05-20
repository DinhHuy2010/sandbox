import logfire


_logger: logfire.Logfire | None = None


def get_logger() -> logfire.Logfire:
    global _logger
    if _logger is None:
        _logger = logfire.configure(local=True)
    return _logger
