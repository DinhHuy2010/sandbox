from __future__ import annotations

import asyncio
import contextvars
import functools
import threading
from typing import Any, Callable, Protocol, overload

__dep_null__ = object()
type Factory[T] = Callable[[], T]


class AbstractDependency[T](Protocol):
    def get(self) -> T:
        raise NotImplementedError("Subclasses must implement .get() method")

    def clear_cache(self) -> None:
        """Clear the cached dependency object, if any
        Warning: this does not close the object if it requires closing
        """

    def is_dependency_created(self) -> bool | None:
        """
        Return True if the dependency is created, i.e. the factory has been called at least once, even if not cached nor cached is clear
        Return None if not supported by the implementation.
        """
        return None


class DependencyFactory[T](Protocol):
    def __call__(self, factory: Factory[T]) -> AbstractDependency[T]:
        raise NotImplementedError("Subclasses must implement __call__ method")


class Dependency[T](AbstractDependency[T]):
    """
    Allow dependency injection
    Warning: not thread-safe, for that use ThreadLocalDependency
    """

    def __init__(self, factory: Factory[T], /, *, cached: bool = False) -> None:
        self._cached_obj = __dep_null__
        self._cached = cached
        self._created = False
        self.factory = factory

    def get(self) -> T:
        if self._cached:
            if self._cached_obj is __dep_null__:
                self._cached_obj = self.factory()
                self._created = True
            return self._cached_obj  # type: ignore[return-value]
        value = self.factory()
        if not self._created:
            self._created = True
        return value

    def clear_cache(self) -> None:
        self._cached_obj = __dep_null__

    def is_dependency_created(self) -> bool | None:
        return self._created


class ThreadLocalDependency[T](AbstractDependency[T]):
    def __init__(self, factory: Factory[T], /) -> None:
        self.factory = factory
        self._local = threading.local()
        self._created = False

    def get(self) -> T:
        if not hasattr(self._local, "cached_obj"):
            self._local.cached_obj = self.factory()
            self._created = True
        return self._local.cached_obj  # type: ignore[return-value]

    def clear_cache(self) -> None:
        if hasattr(self._local, "cached_obj"):
            del self._local.cached_obj

    def is_dependency_created(self) -> bool | None:
        return self._created


class DependencyForAsync[T](AbstractDependency[T]):
    def __init__(self, factory: Factory[T], /) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                "DependencyForAsync can only be used within an async context"
            ) from None
        self.factory = factory
        self._var = contextvars.ContextVar(
            f"dependency_async_cache_{id(self):x}", default=__dep_null__
        )
        self._created = False

    def get(self) -> T:
        cached_obj = self._var.get()
        if cached_obj is __dep_null__:
            cached_obj = self.factory()
            self._created = True
            self._var.set(cached_obj)
        return cached_obj  # type: ignore[return-value]

    def clear_cache(self) -> None:
        self._var.set(__dep_null__)

    def is_dependency_created(self) -> bool | None:
        return self._created


class DependencyWithClosing[T](AbstractDependency[T]):
    def __init__(
        self,
        dependency: AbstractDependency[T],
        /,
        *,
        closer: Callable[[T], bool | None],
    ) -> None:
        self.dependency = dependency
        self.closer = closer

    def get(self) -> T:
        return self.dependency.get()

    def is_dependency_created(self) -> bool | None:
        return self.dependency.is_dependency_created()

    def close(
        self, *, keep_close: bool = False, clear_cache: bool = False
    ) -> bool | None:
        # If dependency is not created, nothing to close
        if not self.dependency.is_dependency_created() and not keep_close:
            return None
        obj = self.dependency.get()
        result = self.closer(obj)
        if clear_cache:
            self.dependency.clear_cache()
        return result

    def __enter__(self) -> DependencyWithClosing[T]:
        return self

    def __exit__(self, *args: Any) -> bool | None:
        return self.close()


class DependencyDescriptor[T]:
    def __init__(self, dep: AbstractDependency[T]) -> None:
        self.dependency = dep

    @overload
    def __get__(self, instance: None, owner: type[object]) -> AbstractDependency[T]: ...
    @overload
    def __get__(self, instance: object, owner: type[object]) -> T: ...
    def __get__(
        self, instance: object, owner: type[object]
    ) -> T | AbstractDependency[T]:
        if instance is None:
            return self.dependency
        return self.dependency.get()


class DependencyDecorator[T](AbstractDependency[T]):
    def __init__(
        self,
        factory: Factory[T],
        /,
        *,
        maker: DependencyFactory[T] | None,
        cached: bool,
    ) -> None:
        self.dependency = dependency(factory, cached=cached, type=maker)
        functools.update_wrapper(self, factory)

    def is_dependency_created(self) -> bool | None:
        return self.dependency.is_dependency_created()

    def get(self) -> T:
        return self.dependency.get()

    def __call__(self) -> T:
        return self.dependency.get()


@overload
def dependency[T](
    factory: Factory[T], /, *, cached: bool = False, type: None = None
) -> Dependency[T]: ...
@overload
def dependency[T](
    factory: Factory[T], /, *, cached: bool = False, type: DependencyFactory[T]
) -> AbstractDependency[T]: ...
def dependency[T](
    factory: Factory[T],
    /,
    *,
    cached: bool = False,
    type: DependencyFactory[T] | None = None,
) -> AbstractDependency[T]:
    if type is not None:
        return type(factory)
    return Dependency(factory, cached=cached)


def inject[T](dep: AbstractDependency[T]) -> DependencyDescriptor[T]:
    return DependencyDescriptor(dep)


def mark_as_dependency[T](
    *, cached: bool = False, type: DependencyFactory[T] | None = None
) -> Callable[[Factory[T]], DependencyDecorator[T]]:
    def wrapper(factory: Factory[T]) -> DependencyDecorator[T]:
        return DependencyDecorator(factory, cached=cached, maker=type)

    return wrapper


def contextable[T](
    dependency: AbstractDependency[T], *, closer: Callable[[T], bool | None]
) -> DependencyWithClosing[T]:
    return DependencyWithClosing(dependency, closer=closer)


def _open_file():
    from tempfile import NamedTemporaryFile

    return NamedTemporaryFile(mode="w+", delete=True)


def _open_db() -> Any:
    db: Any = {}
    print("Database opened")
    return db


class Example:
    file_dep = contextable(
        dependency(_open_file, cached=True), closer=lambda f: f.close()
    )
    db = contextable(
        dependency(_open_db, cached=True), closer=lambda db: print("Database closed")
    )

    def test(self):
        f = self.file_dep.get()
        print(f.name)
        f.write("Hello, Dependency Injection!")
        f.seek(0)
        print(f.read())


def test():
    ex = Example()
    with ex.file_dep:
        ex.test()


if __name__ == "__main__":
    test()
