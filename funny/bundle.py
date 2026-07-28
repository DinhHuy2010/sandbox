import pathlib
from shutil import copyfileobj
import sys

target_dir = pathlib.Path(".") / "eval2"


def build_path(path: pathlib.Path) -> str:
    return f"/mnt/data/{target_dir.name}/{path.relative_to(target_dir).as_posix()}"


for file in target_dir.glob("**/*.py"):
    try:
        f = file.open("rb")
    except Exception:
        continue
    sys.stdout.buffer.write(f"#{build_path(file)}\n".encode())
    with f:
        copyfileobj(f, sys.stdout.buffer)
