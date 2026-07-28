from gzip import GzipFile
import pathlib
from typing import Any

from more_itertools import first
import orjson

try:
    import tkinter.filedialog as fd
except ImportError:
    fd = None


def get_directory(p: Any | None = None) -> pathlib.Path:
    if p is not None:
        f = pathlib.Path(p)
    elif fd is not None:
        f = pathlib.Path(fd.askdirectory())
    else:
        raw = input("Enter directory path: ")
        f = pathlib.Path(raw)
    if f.is_dir():
        return f
    else:
        raise ValueError(f"{f} is not a directory")


def get_file(p: Any | None = None) -> pathlib.Path:
    if p is not None:
        f = pathlib.Path(p)
    elif fd is not None:
        f = pathlib.Path(fd.askopenfilename())
    else:
        raw = input("Enter file path: ")
        f = pathlib.Path(raw)

    if f.is_file():
        return f
    else:
        raise ValueError(f"{f} is not a file")


pd = get_directory("/home/huyonunix/sandbox/temp/gharchive-data")
events = sorted(pd.glob("*.json.gz"))
for p in events:
    with GzipFile(p) as f:
        for d in f:
            p = orjson.loads(d)
            repo = p["repo"]
            if repo == {}:
                continue
            repo_name = repo["name"]
            match p["type"]:
                # case "PushEvent":
                #     payload = p["payload"]
                #     before, head = payload["before"], payload["head"]
                #     print("Pushed to:", payload["ref"])
                #     print("Before:", before)
                #     print("Head:", head)
                #     compare_url = f"https://github.com/{repo_name}/compare/{before[:8]}...{head[:8]}.diff"
                #     print("Compare URL:", compare_url)
                case "PullRequestEvent":
                    payload = p["payload"]
                    action = payload["action"]
                    pr = payload["pull_request"]
                    pr_number = pr["number"]
                    print(f"Pull request #{pr_number} {action}")
                    print("PR URL:", f"https://github.com/{repo_name}/pull/{pr_number}")
                # case "CreateEvent":
                #     print(p["payload"])
                # case _:
                #     print(p["created_at"], p["type"])
