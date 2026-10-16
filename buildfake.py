import argparse
import fileinput
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("input", type=fileinput.FileInput)
parser.add_argument("base", type=pathlib.Path)
args = parser.parse_args()

BASE: pathlib.Path = args.base.resolve()
BASE.mkdir(parents=True, exist_ok=True)
for line in args.input:
    line = line.strip()
    if not line:
        continue
    type, path = line.split(maxsplit=1)
    if type == "directory":
        path = BASE / path
        path.mkdir(parents=True, exist_ok=True)
    elif type == "file":
        path = BASE / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    print(f"Created {type} at {path}")
