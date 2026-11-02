from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import Any


class MountHandler(ABC):
    @abstractmethod
    def listdir(self, path: PurePosixPath) -> list[str]:
        pass

    @abstractmethod
    def stat(self, path: PurePosixPath) -> dict[str, Any]:
        pass

    @abstractmethod
    def read(
        self, path: PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes:
        pass

    def touch(self, path: PurePosixPath) -> None:
        raise NotImplementedError(
            "Write operation is not supported for this mount handler."
        )

    # @abstractmethod
    def write(self, path: PurePosixPath, data: bytes) -> None:
        raise NotImplementedError(
            "Write operation is not supported for this mount handler."
        )

    # @abstractmethod
    def unlink(self, path: PurePosixPath) -> None:
        raise NotImplementedError(
            "Write operation is not supported for this mount handler."
        )

    # @abstractmethod
    def rmdir(self, path: PurePosixPath) -> None:
        raise NotImplementedError(
            "Write operation is not supported for this mount handler."
        )


mountpoints: dict[str, MountHandler] = {}


def resolve(path: str | PurePosixPath) -> tuple[MountHandler, PurePosixPath]:
    path = PurePosixPath(path)

    if not path.is_absolute():
        raise ValueError("VFS paths must be absolute")

    matches = [
        (PurePosixPath(mp), handler)
        for mp, handler in mountpoints.items()
        if path.is_relative_to(mp)
    ]

    if not matches:
        raise ValueError(f"No mountpoint for {path}")

    mp, handler = max(
        matches,
        key=lambda item: len(item[0].parts),
    )

    return handler, path.relative_to(mp)


def mount(mountpoint: str | PurePosixPath, handler: MountHandler) -> None:
    if isinstance(mountpoint, PurePosixPath):
        mountpoint = str(mountpoint)
    mountpoints[mountpoint] = handler


def unmount(mountpoint: str) -> None:
    if mountpoint in mountpoints:
        del mountpoints[mountpoint]
    else:
        raise ValueError(f"Mountpoint not found: {mountpoint}")


def listdir(path: str) -> list[str]:
    handler, relative_path = resolve(path)
    return handler.listdir(relative_path)


def stat(path: str) -> dict[str, Any]:
    handler, relative_path = resolve(path)
    return handler.stat(relative_path)


def read(path: str, start: int = 0, end: int | None = None) -> bytes:
    handler, relative_path = resolve(path)
    return handler.read(relative_path, start, end)


def write(path: str, data: bytes) -> None:
    handler, relative_path = resolve(path)
    handler.write(relative_path, data)


def remove(path: str) -> None:
    handler, relative_path = resolve(path)
    handler.unlink(relative_path)


def rmdir(path: str) -> None:
    handler, relative_path = resolve(path)
    handler.rmdir(relative_path)


def find_mount(path: str | PurePosixPath) -> tuple[str, MountHandler]:
    path = PurePosixPath(path)
    for mountpoint, handler in mountpoints.items():
        if path.is_relative_to(mountpoint):
            return mountpoint, handler
    raise ValueError(f"No mountpoint found for path: {path}")


def walk(path: str | PurePosixPath):
    s = stat(path)
    if s.get("type") != "directory":
        yield from []
        return

    handler, relative_path = resolve(path)
    entries = handler.listdir(relative_path)
    yield path, entries
    for entry in entries:
        entry_path = PurePosixPath(path) / entry
        yield from walk(entry_path)


class ExampleHandler(MountHandler):
    def listdir(self, path: PurePosixPath) -> list[str]:
        match path.as_posix():
            case ".":
                return ["state1", "state2"]
            case "state1":
                return ["file1.txt", "file2.txt"]
            case "state2":
                return ["file3.txt", "file4.txt"]
        raise FileNotFoundError(path)

    def stat(self, path: PurePosixPath):
        match path.as_posix():
            case ".":
                return {"type": "directory"}
            case "state1":
                return {"type": "directory"}
            case "state2":
                return {"type": "directory"}
            case "state1/file1.txt":
                return {"type": "file", "size": 100}
            case "state1/file2.txt":
                return {"type": "file", "size": 200}
            case "state2/file3.txt":
                return {"type": "file", "size": 300}
            case "state2/file4.txt":
                return {"type": "file", "size": 400}
        raise FileNotFoundError(f"Path not found: {path}")

    def read(
        self, path: PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes:
        match path.as_posix():
            case "state1/file1.txt":
                return b"Content of file1.txt"
            case "state1/file2.txt":
                return b"Content of file2.txt"
            case "state2/file3.txt":
                return b"Content of file3.txt"
            case "state2/file4.txt":
                return b"Content of file4.txt"
        raise FileNotFoundError(f"Path not found: {path}")


class RootHandler(MountHandler):
    def _is_root(self, path: PurePosixPath) -> bool:
        return path.parts == ()

    def listdir(self, path: PurePosixPath) -> list[str]:
        if path == PurePosixPath("."):
            return [
                PurePosixPath(mp).name
                for mp in mountpoints
                if mp != "/" and len(PurePosixPath(mp).parts) == 2
            ]

        raise FileNotFoundError(path)

    def stat(self, path: PurePosixPath) -> dict[str, Any]:
        if self._is_root(path) or str(path) in mountpoints:
            return {"type": "directory"}
        else:
            raise FileNotFoundError(f"Path not found: {path}")

    def read(self, path: PurePosixPath) -> bytes:
        raise IsADirectoryError(f"Path is a directory: {path}")

    def write(self, path: PurePosixPath, data: bytes) -> None:
        raise IsADirectoryError(f"Path is a directory: {path}")

    def unlink(self, path: PurePosixPath) -> None:
        raise IsADirectoryError(f"Path is a directory: {path}")

    def rmdir(self, path: PurePosixPath) -> None:
        raise IsADirectoryError(f"Path is a directory: {path}")


class FileHandler(ABC):
    @abstractmethod
    def read(self, start: int = 0, end: int | None = None) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes) -> None:
        pass

    @abstractmethod
    def stat(self) -> dict[str, Any]:
        pass


class StaticFileHandler(FileHandler):
    def __init__(self, content: bytes):
        self.content = content

    def read(self, start: int = 0, end: int | None = None) -> bytes:
        return self.content[start:end]

    def write(self, data: bytes) -> None:
        raise NotImplementedError("Write operation is not supported for static files.")

    def stat(self) -> dict[str, Any]:
        return {"type": "file", "size": len(self.content)}


class DynamicMount(MountHandler):
    def __init__(self, files: dict[str, FileHandler]):
        self.tree = {}
        for path, handler in files.items():
            parts = PurePosixPath(path).parts
            current = self.tree
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = handler

    def listdir(self, path: PurePosixPath) -> list[str]:
        current = self._get_node(path)
        if isinstance(current, dict):
            return list(current.keys())
        raise NotADirectoryError(f"Path is not a directory: {path}")

    def stat(self, path: PurePosixPath) -> dict[str, Any]:
        current = self._get_node(path)
        if isinstance(current, dict):
            return {"type": "directory"}
        elif isinstance(current, FileHandler):
            return {"type": "file", "size": len(current.read())}
        raise FileNotFoundError(f"Path not found: {path}")

    def read(
        self, path: PurePosixPath, start: int = 0, end: int | None = None
    ) -> bytes:
        current = self._get_node(path)
        if isinstance(current, FileHandler):
            return current.read(start, end)
        raise IsADirectoryError(f"Path is a directory: {path}")

    def write(self, path: PurePosixPath, data: bytes) -> None:
        current = self._get_node(path)
        if isinstance(current, FileHandler):
            current.write(data)
        else:
            raise IsADirectoryError(f"Path is a directory: {path}")

    def unlink(self, path: PurePosixPath) -> None:
        parts = path.parts
        current = self.tree
        for part in parts[:-1]:
            current = current.get(part)
            if current is None:
                raise FileNotFoundError(f"Path not found: {path}")
        if parts[-1] in current:
            del current[parts[-1]]
        else:
            raise FileNotFoundError(f"Path not found: {path}")

    def rmdir(self, path: PurePosixPath) -> None:
        parts = path.parts
        current = self.tree
        for part in parts[:-1]:
            current = current.get(part)
            if current is None:
                raise FileNotFoundError(f"Path not found: {path}")
        if parts[-1] in current and isinstance(current[parts[-1]], dict):
            del current[parts[-1]]
        else:
            raise NotADirectoryError(f"Path is not a directory: {path}")

    def _get_node(self, path: PurePosixPath) -> Any:
        current = self.tree
        for part in path.parts:
            current = current.get(part)
            if current is None:
                raise FileNotFoundError(f"Path not found: {path}")
        return current

    def add_file(self, path: str, handler: FileHandler) -> None:
        parts = PurePosixPath(path).parts
        current = self.tree
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = handler


files = {
    "about/version": StaticFileHandler(b"1.0.0"),
    "about/license": StaticFileHandler(b"MIT License"),
    "about/author": StaticFileHandler(b"John Doe"),
    "about/something/else": StaticFileHandler(b"Some other content"),
}

mount("/example", ExampleHandler())
mount("/", RootHandler())
mount("/dynamic", DynamicMount(files))
for f in walk("/"):
    for e in f[1]:
        p = PurePosixPath(f[0]) / e
        if stat(p).get("type") == "file":
            print(f"{p}: {stat(str(p))['size']} bytes")
            print(read(str(p)).decode())
