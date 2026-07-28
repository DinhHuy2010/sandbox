# pyright: standard

import threading
from typing import MutableMapping

from dotenv import dotenv_values


class Secrets(MutableMapping[str, str]):
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._secrets = {}

    def store(self, key: str, value: str) -> None:
        with self._lock:
            self._secrets[key.upper()] = value

    def retrieve(self, key: str) -> str:
        with self._lock:
            return self._secrets[key.upper()]

    def delete(self, key: str) -> None:
        with self._lock:
            if key.upper() in self._secrets:
                del self._secrets[key.upper()]

    def list_secrets(self) -> list[str]:
        with self._lock:
            return list(self._secrets.keys())

    def clear(self) -> None:
        with self._lock:
            self._secrets.clear()

    def has_secret(self, key: str) -> bool:
        with self._lock:
            return key.upper() in self._secrets

    def __getattr__(self, name: str) -> str:
        with self._lock:
            if name.upper() in self._secrets:
                return self._secrets[name.upper()]
            else:
                raise AttributeError(f"'Secrets' object has no attribute '{name}'")

    def __contains__(self, key):
        with self._lock:
            return key.upper() in self._secrets

    __getitem__ = retrieve
    __setitem__ = store
    __delitem__ = delete

    def __iter__(self):
        return iter(self._secrets)

    def __len__(self):
        return len(self._secrets)

    @classmethod
    def empty(cls) -> "Secrets":
        return cls()

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "Secrets":
        secrets = cls()
        config = dotenv_values(env_file)
        for key, value in config.items():
            if value is not None:
                secrets.store(key, value)
        return secrets


# type EnvironType = MutableMapping[str, str]


# def env() -> EnvironType:
#     import os

#     return os.environ

# env()

# f = tempfile.NamedTemporaryFile(suffix=".tar.gz")
# with tarfile.TarFile.open(fileobj=f, mode="w:gz") as zf:
#     for _ in range(5000):
#         # zf.makefile(f"file{_}.txt", f"This is the content of file {_}.")
#         tarinfo = tarfile.TarInfo(name=f"file{_}.txt")
#         content = f"This is the content of file {_}.".encode("utf-8")
#         tarinfo.size = len(content)
#         zf.addfile(tarinfo, fileobj=BytesIO(content))

# f.seek(0)
# sys.stdout.buffer.write(f.read())
