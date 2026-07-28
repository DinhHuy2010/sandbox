from datetime import datetime

from eval2.core import Context
from eval2.builtins import Expression


def sleep(seconds: float) -> Expression[None]:
    def evaluate(ctx: Context) -> None:
        import time

        time.sleep(seconds)

    return Expression(evaluate)


def current_time() -> Expression[datetime]:
    def evaluate(ctx: Context) -> datetime:
        return datetime.now()

    return Expression(evaluate)
