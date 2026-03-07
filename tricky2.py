from typing import Any

import audit
import subprocess
import httpx

@audit.handle_for_audit("open")
def onopen(path: str, mode: str, flags: int) -> None:
    print("open(%r, %r)" % (path, mode))


@audit.handle_for_audit("import")
def onimport(name: str, *args: Any) -> None:
    print("import %r" % (name,))


@audit.handle_for_audit("subprocess.Popen")
def on_popen(executable: str, args: list[str], cwd: str, env: dict[str, str]) -> None:
    print("Opening subprocess: %s %r" % (executable, " ".join(args[1:])))

audit.inject()

httpx.get("https://www.google.com/")

def main():
    print("Hello, World!")
    input("What is your name? ")
    subprocess.Popen(["echo", "Hello, subprocess!"], cwd=".", env={"EXAMPLE": "value"})

if __name__ == "__main__":
    main()
