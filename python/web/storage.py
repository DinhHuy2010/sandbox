# pyright: strict

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO, UnsupportedOperation
from typing import IO, Any, Iterable, LiteralString

from pydantic import BaseModel, JsonValue


@dataclass
class StoragePanic(Exception):
    code: str
    details: str


class EntityNamespaces(StrEnum):
    storage = "storage"


def create_type(namespace: EntityNamespaces | LiteralString, entity: str) -> str:
    return f"{namespace}:{entity}"


class EntityMetadata(BaseModel):
    created_at: datetime.datetime
    last_modified_at: datetime.datetime
    size: int = -1
    extra: dict[str, JsonValue]


type ValidDataType = bytes


class EntityData(BaseModel):
    type: str
    path: str
    metadata: EntityMetadata


VALID_IO_MODES = {
    "rb",
    "r+b",
    "wb",
    "w+b",
    "ab",
    "a+b",
}


class StorageInterface(ABC):
    @abstractmethod
    def create_entity(
        self,
        entity_type: str,
        path: str,
        extra_metadata: dict[str, JsonValue] | None = None,
    ) -> EntityData: ...

    @abstractmethod
    def read_entity(self, path: str) -> EntityData: ...

    @abstractmethod
    def update_entity(
        self,
        path: str,
        extra_metadata: dict[str, JsonValue] | None = None,
        entity_type: str | None = None,
    ) -> EntityData: ...

    @abstractmethod
    def delete_entity(self, path: str) -> None: ...

    @abstractmethod
    def query_entities(
        self,
        entity_type: str | None = None,
        path_prefix: str | None = None,
    ) -> Iterable[EntityData]: ...

    @abstractmethod
    def read_entity_content(self, path: str) -> ValidDataType: ...
    @abstractmethod
    def replace_entity_content(self, path: str, data: ValidDataType) -> EntityData: ...
    @abstractmethod
    def open_entity_content_as_io(self, path: str, mode: str = "rb") -> IO[bytes]: ...


class StorageContentIOInterface(BytesIO):
    def __init__(self, storage: StorageInterface, path: str, content: bytes, mode: str):
        super().__init__(content)
        self._storage = storage
        self._path = path
        self._mode = mode

    def readable(self):
        return "r" in self._mode or "+" in self._mode

    def writable(self):
        return "w" in self._mode or "a" in self._mode or "+" in self._mode

    def close(self) -> None:
        if not self.closed and self.writable():
            try:
                self._storage.replace_entity_content(self._path, self.getvalue())
            except Exception as e:
                raise StoragePanic(
                    "write-failed",
                    f"Failed to write content to entity at path {self._path!r}: {e}",
                ) from e
            finally:
                super().close()

    def write(self, buffer: Any) -> int:
        if not self.writable():
            raise UnsupportedOperation("not writable")
        if "a" in self._mode:
            self.seek(0, 2)  # Move to the end of the stream for append mode
        return super().write(buffer)

    def read(self, size: int | None = -1) -> bytes:
        if not self.readable():
            raise UnsupportedOperation("not readable")
        return super().read(size)

    def readinto(self, buffer: Any) -> int:
        if not self.readable():
            raise UnsupportedOperation("not readable")
        return super().readinto(buffer)

    def readline(self, size: int | None = -1) -> bytes:
        if not self.readable():
            raise UnsupportedOperation("not readable")
        return super().readline(size)

    def readlines(self, hint: int | None = -1) -> list[bytes]:
        if not self.readable():
            raise UnsupportedOperation("not readable")
        return super().readlines(hint)

    def writelines(self, lines: Iterable[Any]) -> None:
        if not self.writable():
            raise UnsupportedOperation("not writable")
        if "a" in self._mode:
            self.seek(0, 2)
        return super().writelines(lines)

    def truncate(self, size: int | None = None) -> int:
        if not self.writable():
            raise UnsupportedOperation("not writable")
        return super().truncate(size)


class StorageInMemory(StorageInterface):
    def __init__(self):
        self._storage_metadata: dict[str, EntityData] = {}
        self._data: dict[str, ValidDataType] = {}

    @staticmethod
    def _now() -> datetime.datetime:
        return datetime.datetime.now(tz=datetime.timezone.utc)

    @staticmethod
    def _size(data: ValidDataType) -> int:
        return len(data)

    def _ensure_exists(self, path: str) -> EntityData:
        try:
            return self._storage_metadata[path]
        except KeyError:
            raise StoragePanic(
                "entity-not-found",
                f"Entity at path {path!r} does not exist.",
            )

    def _set_content(self, path: str, data: ValidDataType) -> EntityData:
        entity = self._ensure_exists(path)
        metadata = entity.metadata.model_copy(deep=True)
        metadata.size = self._size(data)
        metadata.last_modified_at = self._now()

        updated = EntityData(
            type=entity.type,
            path=entity.path,
            metadata=metadata,
        )
        self._storage_metadata[path] = updated
        self._data[path] = data
        return updated.model_copy(deep=True)

    def create_entity(
        self,
        entity_type: str,
        path: str,
        extra_metadata: dict[str, JsonValue] | None = None,
    ) -> EntityData:
        if path in self._storage_metadata:
            raise StoragePanic(
                "entity-exists",
                f"Entity at path {path!r} already exists.",
            )

        now = self._now()
        entity = EntityData(
            type=entity_type,
            path=path,
            metadata=EntityMetadata(
                created_at=now,
                last_modified_at=now,
                size=0,
                extra=extra_metadata.copy() if extra_metadata is not None else {},
            ),
        )
        self._storage_metadata[path] = entity
        self._data[path] = b""
        return entity.model_copy(deep=True)

    def read_entity(self, path: str) -> EntityData:
        return self._ensure_exists(path).model_copy(deep=True)

    def update_entity(
        self,
        path: str,
        extra_metadata: dict[str, JsonValue] | None = None,
        entity_type: str | None = None,
    ) -> EntityData:
        entity = self._ensure_exists(path)
        metadata = entity.metadata.model_copy(deep=True)
        if extra_metadata is not None:
            metadata.extra.update(extra_metadata)
        metadata.last_modified_at = self._now()

        updated = EntityData(
            type=entity_type if entity_type is not None else entity.type,
            path=entity.path,
            metadata=metadata,
        )
        self._storage_metadata[path] = updated
        return updated.model_copy(deep=True)

    def delete_entity(self, path: str) -> None:
        self._ensure_exists(path)
        del self._storage_metadata[path]
        del self._data[path]

    def query_entities(
        self,
        entity_type: str | None = None,
        path_prefix: str | None = None,
    ) -> Iterable[EntityData]:
        for entity in self._storage_metadata.values():
            if entity_type is not None and entity.type != entity_type:
                continue
            if path_prefix is not None and not entity.path.startswith(path_prefix):
                continue
            yield entity.model_copy(deep=True)

    def read_entity_content(self, path: str) -> ValidDataType:
        self._ensure_exists(path)
        return self._data[path]

    def replace_entity_content(self, path: str, data: ValidDataType) -> EntityData:
        return self._set_content(path, data)

    def open_entity_content_as_io(self, path: str, mode: str = "rb") -> IO[bytes]:
        self._ensure_exists(path)
        if mode not in VALID_IO_MODES:
            raise StoragePanic(
                "unsupported-mode",
                f"Unsupported IO mode {mode!r}. Supported modes are: {', '.join(sorted(VALID_IO_MODES))}.",
            )

        content = b"" if "w" in mode else self._data[path]
        stream = StorageContentIOInterface(self, path, content, mode=mode)
        if "a" in mode:
            stream.seek(0, 2)
        return stream


def demo():

    def dump_entities(
        storage: StorageInterface,
        entity_type: str | None = None,
        path_prefix: str | None = None,
    ):
        entities = storage.query_entities(
            entity_type=entity_type, path_prefix=path_prefix
        )
        for entity in entities:
            print(f"Path: {entity.path}")
            print(f"Type: {entity.type}")
            print(f"Metadata: {entity.metadata}")
            print(f"Data: {storage.read_entity_content(entity.path)}")
            print("-" * 40)

    import zoneinfo
    import json

    tzs = zoneinfo.available_timezones()
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    tz_type = create_type("datetime", "timezone")

    storage = StorageInMemory()
    for tz in tzs:
        zi = zoneinfo.ZoneInfo(tz)
        name = zi.tzname(now)
        offset = (
            zi.utcoffset(now).total_seconds() if zi.utcoffset(now) is not None else 0  # type: ignore
        )
        dst = zi.dst(now).total_seconds() if zi.dst(now) is not None else 0  # type: ignore
        storage.create_entity(
            tz_type,
            f"/timezones/{tz}",
            {
                "name": tz,
                "full_name": zoneinfo.ZoneInfo(tz).key,
                "other_names": [name] if name is not None else [],
            },
        )
        blob = json.dumps({"name": tz, "offset": offset, "dst": dst}).encode("utf-8")
        with storage.open_entity_content_as_io(f"/timezones/{tz}", mode="wb") as f:
            f.write(blob)
    # print(storage.query_entities(entity_type=tz_type, path_prefix="/timezones"))
    dump_entities(storage, entity_type=tz_type, path_prefix="/timezones")


if __name__ == "__main__":
    demo()
