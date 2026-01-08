from collections.abc import Mapping
from types import TracebackType
from typing import Any, Callable, Unpack

type ExcArgs = tuple[
    type[BaseException] | None,
    BaseException | None,
    TracebackType | None,
]

type GetResourceCallable[T] = Callable[[], T]
type CloseResourceCallable[T] = Callable[[T, Unpack[ExcArgs]], bool | None]
type ResourceUser[T, F] = Callable[[T], F]


class _LifespanNull:
    pass


class _ExceptionSuppressed:
    pass


_LifespanNull_ = _LifespanNull()
EXCEPTION_SUPPRESSED = _ExceptionSuppressed()


class resource_lifespan[T]:
    def __init__(
        self,
        get_resource: GetResourceCallable[T],
        close_resource: CloseResourceCallable[T] | None = None,
    ) -> None:
        self._get_resource = get_resource
        self._close_resource = close_resource
        self.resource: T | _LifespanNull = _LifespanNull_
        self._marked_as_unusable = False

    def get_resource(self) -> T:
        if self._marked_as_unusable:
            raise RuntimeError("Resource has been marked as unusable.")
        if isinstance(self.resource, _LifespanNull):
            self.resource = self._get_resource()
        return self.resource

    def close_resource(self, *exc_args: Unpack[ExcArgs]) -> None:
        if self._marked_as_unusable:
            return
        if not isinstance(self.resource, _LifespanNull):
            if self._close_resource:
                self._close_resource(self.resource, *exc_args)
            self.resource = _LifespanNull_

    def use_resource[F](self, user: ResourceUser[T, F]) -> F | _ExceptionSuppressed:
        try:
            result = user(self.get_resource())
        except BaseException as exc:
            if self.close_resource(type(exc), exc, exc.__traceback__):
                return EXCEPTION_SUPPRESSED
            raise
        else:
            self.close_resource(None, None, None)
            return result

    def need_resource[F](
        self,
    ) -> Callable[[ResourceUser[T, F]], Callable[[], F | _ExceptionSuppressed]]:
        def decorator(
            user: ResourceUser[T, F],
        ) -> Callable[[], F | _ExceptionSuppressed]:
            def wrapper() -> F | _ExceptionSuppressed:
                return self.use_resource(user)

            return wrapper

        return decorator

    def __enter__(self) -> T:
        resource = self.get_resource()
        return resource

    def __exit__(
        self,
        *exc_args: Unpack[ExcArgs],
    ) -> bool | None:
        return self.close_resource(*exc_args)

    def mark_resource_as_unusable(self) -> None:
        self.close_resource(None, None, None)  # Ensure resource is closed
        self._marked_as_unusable = True

def open_db():
    print("Opening database connection")
    return "db_connection"

def close_db(conn: Any, *_: Any) -> None:
    print("Closing database connection")
    return None

db_lifespan = resource_lifespan(open_db, close_db)
# Example usage:
with db_lifespan as db_conn:
    print(f"Using {db_conn}")

# Example usage:
def use_db(conn: str) -> None:
    print(f"Using {conn}")

db_lifespan.use_resource(use_db)

# Example usage with decorator:
@db_lifespan.need_resource()
def decorated_use_db(conn: str) -> None:
    print(f"Using {conn}")

decorated_use_db()

# Example usage:
db_lifespan.mark_resource_as_unusable()
with db_lifespan as db_conn:
    print(f"Using {db_conn}")  # This will raise RuntimeError
