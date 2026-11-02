"""Mountable virtual filesystem with memory, indexed SQLite, and host backends.

Paths are POSIX-style absolute paths. No symlinks are followed by this VFS.
HostMount is intended for trusted local paths; do not expose it to untrusted callers.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


@dataclass(frozen=True, slots=True)
class VFSStat:
    type: str
    size: int = 0


def _absolute(path: str | PurePosixPath) -> PurePosixPath:
    raw = str(path)
    if not raw.startswith("/"):
        raise ValueError(f"Expected absolute VFS path: {raw}")
    parts = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError("Path escapes VFS root")
            parts.pop()
        else:
            parts.append(part)
    return PurePosixPath("/" + "/".join(parts))


def _relative(path: str | PurePosixPath) -> PurePosixPath:
    raw = str(path)
    if raw.startswith("/"):
        raise ValueError(f"Expected relative backend path: {raw}")
    parts = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("Parent traversal is forbidden in backend paths")
        parts.append(part)
    return PurePosixPath(*parts)


def _slice(data: bytes, start: int = 0, end: int | None = None) -> bytes:
    if start < 0 or (end is not None and end < start):
        raise ValueError("Invalid byte range")
    return data[start:end]


class FileHandler(ABC):
    @abstractmethod
    def read(self, start: int = 0, end: int | None = None) -> bytes: ...
    @abstractmethod
    def stat(self) -> VFSStat: ...
    def write(self, data: bytes) -> None:
        raise PermissionError("File is read-only")


class StaticFileHandler(FileHandler):
    def __init__(self, content: bytes):
        self.content = bytes(content)

    def read(self, start: int = 0, end: int | None = None) -> bytes:
        return _slice(self.content, start, end)

    def stat(self) -> VFSStat:
        return VFSStat("file", len(self.content))


class MemoryFileHandler(StaticFileHandler):
    def write(self, data: bytes) -> None:
        self.content = bytes(data)


class MountHandler(ABC):
    @abstractmethod
    def iterdir(self, path: PurePosixPath) -> Iterator[str]: ...
    @abstractmethod
    def stat(self, path: PurePosixPath) -> VFSStat: ...
    @abstractmethod
    def read(
        self, path: PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes: ...
    def write(self, path: PurePosixPath, data: bytes) -> None:
        raise PermissionError("Mount is read-only")

    def touch(self, path: PurePosixPath) -> None:
        raise PermissionError("Mount is read-only")

    def mkdir(self, path: PurePosixPath) -> None:
        raise PermissionError("Mount is read-only")

    def unlink(self, path: PurePosixPath) -> None:
        raise PermissionError("Mount is read-only")

    def rmdir(self, path: PurePosixPath) -> None:
        raise PermissionError("Mount is read-only")


class MemoryMount(MountHandler):
    """Mutable tree. Directories are dictionaries; files are FileHandler objects."""

    def __init__(self, files: Mapping[str, FileHandler] | None = None):
        self.tree: dict[str, Any] = {}
        for path, handler in (files or {}).items():
            self.add_file(path, handler)

    def _node(self, path: PurePosixPath) -> Any:
        node: Any = self.tree
        for part in _relative(path).parts:
            if not isinstance(node, dict):
                raise NotADirectoryError(str(path))
            if part not in node:
                raise FileNotFoundError(str(path))
            node = node[part]
        return node

    def _parent(self, path: PurePosixPath) -> tuple[dict[str, Any], str]:
        path = _relative(path)
        if not path.parts:
            raise PermissionError("Cannot modify mount root")
        parent = self._node(path.parent)
        if not isinstance(parent, dict):
            raise NotADirectoryError(str(path.parent))
        return parent, path.name

    def iterdir(self, path: PurePosixPath) -> Iterator[str]:
        node = self._node(path)
        if not isinstance(node, dict):
            raise NotADirectoryError(str(path))
        yield from node

    def stat(self, path: PurePosixPath) -> VFSStat:
        node = self._node(path)
        if isinstance(node, dict):
            return VFSStat("directory")
        return node.stat()

    def read(
        self, path: PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes:
        node = self._node(path)
        if isinstance(node, dict):
            raise IsADirectoryError(str(path))
        return node.read(start, end)

    def write(self, path: PurePosixPath, data: bytes) -> None:
        node = self._node(path)
        if isinstance(node, dict):
            raise IsADirectoryError(str(path))
        node.write(data)

    def touch(self, path: PurePosixPath) -> None:
        parent, name = self._parent(path)
        if name not in parent:
            parent[name] = MemoryFileHandler(b"")
        elif isinstance(parent[name], dict):
            raise IsADirectoryError(str(path))

    def mkdir(self, path: PurePosixPath) -> None:
        parent, name = self._parent(path)
        if name in parent:
            raise FileExistsError(str(path))
        parent[name] = {}

    def add_file(self, path: str, handler: FileHandler) -> None:
        relative = _relative(path)
        if not relative.parts:
            raise ValueError("File path cannot be root")
        node: dict[str, Any] = self.tree
        for part in relative.parts[:-1]:
            child = node.setdefault(part, {})
            if not isinstance(child, dict):
                raise NotADirectoryError(part)
            node = child
        if relative.name in node:
            raise FileExistsError(str(relative))
        node[relative.name] = handler

    def unlink(self, path: PurePosixPath) -> None:
        parent, name = self._parent(path)
        if name not in parent:
            raise FileNotFoundError(str(path))
        if isinstance(parent[name], dict):
            raise IsADirectoryError(str(path))
        del parent[name]

    def rmdir(self, path: PurePosixPath) -> None:
        parent, name = self._parent(path)
        if name not in parent:
            raise FileNotFoundError(str(path))
        node = parent[name]
        if not isinstance(node, dict):
            raise NotADirectoryError(str(path))
        if node:
            raise OSError("Directory not empty")
        del parent[name]


DynamicMount = MemoryMount


class IndexedMount(MountHandler):
    """Read-only directory index in SQLite; file contents are not stored."""

    def __init__(self, database: str | Path):
        self.connection = sqlite3.connect(str(database))
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS nodes "
            "(path TEXT PRIMARY KEY, parent TEXT NOT NULL, name TEXT NOT NULL, "
            "kind TEXT NOT NULL, size INTEGER NOT NULL DEFAULT 0)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent)"
        )
        self.connection.execute(
            "INSERT OR IGNORE INTO nodes(path,parent,name,kind,size) "
            "VALUES ('','','','directory',0)"
        )
        self.connection.commit()

    def add_entries(self, entries: Iterator[tuple[str, int]] | Any) -> None:
        """Bulk-index (relative_path, size). Commit per call."""
        batch = []
        for raw, size in entries:
            path = _relative(raw)
            if not path.parts:
                continue
            for i in range(1, len(path.parts)):
                parent = "/".join(path.parts[: i - 1])
                name = path.parts[i - 1]
                full = "/".join(path.parts[:i])
                batch.append((full, parent, name, "directory", 0))
            full = path.as_posix()
            batch.append(
                (
                    full,
                    path.parent.as_posix() if len(path.parts) > 1 else "",
                    path.name,
                    "file",
                    int(size),
                )
            )
            if len(batch) >= 10000:
                self.connection.executemany(
                    "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?)", batch
                )
                batch.clear()
        if batch:
            self.connection.executemany(
                "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?)", batch
            )
        self.connection.commit()

    def stat(self, path: PurePosixPath) -> VFSStat:
        key = "" if str(path) == "." else _relative(path).as_posix()
        row = self.connection.execute(
            "SELECT kind,size FROM nodes WHERE path=?", (key,)
        ).fetchone()
        if row is None:
            raise FileNotFoundError(str(path))
        return VFSStat(row[0], row[1])

    def iterdir(self, path: PurePosixPath) -> Iterator[str]:
        if self.stat(path).type != "directory":
            raise NotADirectoryError(str(path))
        key = "" if str(path) == "." else _relative(path).as_posix()
        cursor = self.connection.execute(
            "SELECT name FROM nodes WHERE parent=? AND path != '' ORDER BY name", (key,)
        )
        for (name,) in cursor:
            yield name

    def read(
        self, path: PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes:
        if self.stat(path).type == "directory":
            raise IsADirectoryError(str(path))
        raise NotImplementedError("IndexedMount stores metadata, not file contents")

    def close(self) -> None:
        self.connection.close()


class HostMount(MountHandler):
    """Trusted-only adapter. Symlinks are rejected at every path component."""

    def __init__(self, root: str | Path, read_only: bool = True):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise NotADirectoryError(str(root))
        self.read_only = read_only

    def _host(self, path: PurePosixPath) -> Path:
        target = self.root
        for part in _relative(path).parts:
            target = target / part
            if target.is_symlink():
                raise PermissionError("Host symlinks are not supported")
        return target

    def stat(self, path: PurePosixPath) -> VFSStat:
        target = self._host(path)
        s = target.stat()
        if target.is_dir():
            return VFSStat("directory")
        if target.is_file():
            return VFSStat("file", s.st_size)
        raise OSError("Unsupported host node type")

    def iterdir(self, path: PurePosixPath) -> Iterator[str]:
        target = self._host(path)
        if not target.is_dir():
            raise NotADirectoryError(str(path))
        with __import__("os").scandir(target) as it:
            for entry in it:
                if not entry.is_symlink():
                    yield entry.name

    def read(
        self, path: PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes:
        if start < 0 or (end is not None and end < start):
            raise ValueError("Invalid byte range")
        target = self._host(path)
        with target.open("rb") as f:
            f.seek(start)
            return f.read(None if end is None else end - start)

    def _writable(self):
        if self.read_only:
            raise PermissionError("Mount is read-only")

    def write(self, path: PurePosixPath, data: bytes) -> None:
        self._writable()
        self._host(path).write_bytes(data)

    def touch(self, path: PurePosixPath) -> None:
        self._writable()
        self._host(path).touch(exist_ok=True)

    def mkdir(self, path: PurePosixPath) -> None:
        self._writable()
        self._host(path).mkdir()

    def unlink(self, path: PurePosixPath) -> None:
        self._writable()
        self._host(path).unlink()

    def rmdir(self, path: PurePosixPath) -> None:
        self._writable()
        self._host(path).rmdir()


class VirtualFS:
    def __init__(self):
        self.mounts: dict[PurePosixPath, MountHandler] = {}

    def mount(self, path: str, handler: MountHandler) -> None:
        key = _absolute(path)
        if key in self.mounts:
            raise FileExistsError(f"Mount already exists: {key}")
        self.mounts[key] = handler

    def unmount(self, path: str) -> None:
        key = _absolute(path)
        if key not in self.mounts:
            raise FileNotFoundError(str(key))
        del self.mounts[key]

    def resolve(self, path: str | PurePosixPath) -> tuple[MountHandler, PurePosixPath]:
        path = _absolute(path)
        matches = [mp for mp in self.mounts if path.is_relative_to(mp)]
        if not matches:
            raise FileNotFoundError(f"No mount for {path}")
        mp = max(matches, key=lambda x: len(x.parts))
        return self.mounts[mp], _relative(path.relative_to(mp))

    def _synthetic_children(self, path: PurePosixPath) -> set[str]:
        return {
            mp.relative_to(path).parts[0]
            for mp in self.mounts
            if mp != path and mp.is_relative_to(path)
        }

    def _is_synthetic_dir(self, path: PurePosixPath) -> bool:
        return path == PurePosixPath("/") or bool(self._synthetic_children(path))

    def stat(self, path: str | PurePosixPath) -> VFSStat:
        path = _absolute(path)
        if path in self.mounts or self._is_synthetic_dir(path):
            if path not in self.mounts:
                return VFSStat("directory")
        try:
            handler, relative = self.resolve(path)
            return handler.stat(relative)
        except (FileNotFoundError, NotADirectoryError):
            if self._is_synthetic_dir(path):
                return VFSStat("directory")
            raise

    def iterdir(self, path: str | PurePosixPath) -> Iterator[str]:
        path = _absolute(path)
        if self.stat(path).type != "directory":
            raise NotADirectoryError(str(path))
        names = self._synthetic_children(path)
        try:
            handler, relative = self.resolve(path)
            names.update(handler.iterdir(relative))
        except (FileNotFoundError, NotADirectoryError):
            if not self._is_synthetic_dir(path):
                raise
        yield from sorted(names)

    def listdir(self, path: str | PurePosixPath) -> list[str]:
        return list(self.iterdir(path))

    def read(
        self, path: str | PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes:
        handler, relative = self.resolve(path)
        return handler.read(relative, start, end)

    def _mutate(self, operation: str, path: str | PurePosixPath, *args: Any) -> None:
        absolute = _absolute(path)
        if absolute in self.mounts or self._is_synthetic_dir(absolute):
            raise PermissionError("Cannot modify mountpoint or virtual mount directory")
        handler, relative = self.resolve(absolute)
        getattr(handler, operation)(relative, *args)

    def write(self, path: str | PurePosixPath, data: bytes) -> None:
        self._mutate("write", path, data)

    def touch(self, path: str | PurePosixPath) -> None:
        self._mutate("touch", path)

    def mkdir(self, path: str | PurePosixPath) -> None:
        self._mutate("mkdir", path)

    def unlink(self, path: str | PurePosixPath) -> None:
        self._mutate("unlink", path)

    def rmdir(self, path: str | PurePosixPath) -> None:
        self._mutate("rmdir", path)

    def walk(
        self, path: str | PurePosixPath = "/"
    ) -> Iterator[tuple[PurePosixPath, list[str]]]:
        root = _absolute(path)
        if self.stat(root).type != "directory":
            return
        stack = [root]
        while stack:
            current = stack.pop()
            entries = self.listdir(current)
            yield current, entries
            for name in reversed(entries):
                child = current / name
                if self.stat(child).type == "directory":
                    stack.append(child)


if __name__ == "__main__":
    vfs = VirtualFS()
    vfs.mount(
        "/example",
        MemoryMount(
            {
                "state1/file1.txt": StaticFileHandler(b"Content of file1.txt"),
                "state1/file2.txt": StaticFileHandler(b"Content of file2.txt"),
                "state2/file3.txt": StaticFileHandler(b"Content of file3.txt"),
                "state2/file4.txt": StaticFileHandler(b"Content of file4.txt"),
            }
        ),
    )
    vfs.mount(
        "/dynamic",
        MemoryMount(
            {
                "about/version": StaticFileHandler(b"1.0.0"),
                "about/license": StaticFileHandler(b"MIT License"),
                "about/author": StaticFileHandler(b"John Doe"),
                "about/something/else": StaticFileHandler(b"Some other content"),
            }
        ),
    )
    for directory, entries in vfs.walk():
        for entry in entries:
            path = directory / entry
            info = vfs.stat(path)
            if info.type == "file":
                print(f"{path}: {info.size} bytes")
                print(vfs.read(path).decode())
