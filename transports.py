import sys
from collections import Counter
from typing import cast

import httpx

c = Counter()


def on_approve(message: str):
    print(f"✅ Approved for {message}")


def on_reject(message: str):
    print(f"❌ Rejected for {message}")
    raise Exception(f"Operation rejected for {message}")


def approve_for(message: str):
    while True:
        user_input = input(f"Approve {message}? (y/n): ").strip().lower()
        if user_input == "y":
            on_approve(message)
            return True
        elif user_input == "n":
            on_reject(message)
            return False
        else:
            print("Invalid input. Please enter 'y' for yes or 'n' for no.")


import_cache_ok = {}


def audit_hook(event, args):
    c[event] += 1
    if event == "socket.connect":
        (_, (address_host, address_port)) = args
        if approve_for(f"connect to {address_host}:{address_port}"):
            print(f"Socket connect to {address_host}:{address_port}")
        else:
            raise Exception(
                f"Connection to {address_host}:{address_port} rejected by user."
            )
    elif event == "open":
        (path, mode, flags) = args
        if not isinstance(path, str):
            # print(f"Open file with non-string path: {path} and mode: {mode}")
            return
        if not cast(str, path).startswith((sys.prefix, sys.base_prefix)):
            print(f"Open file: {path} with mode: {mode}")
    elif event == "os.listdir":
        (path,) = args
        if not cast(str, path).startswith((sys.prefix, sys.base_prefix)):
            if not approve_for(f"list directory {path}"):
                raise Exception(f"Listing directory {path} rejected by user.")
    elif event == "import":
        module, filename, sys_path, sys_meta_path, sys_path_hooks = args
        print(f"Importing module: {module}")
        print("sys.path:")
        for p in sys_path:
            print(f"  - {p}")
        module = module.split(".")[0]  # Check only the top-level module
        if not import_cache_ok.get(module, False):
            ok = approve_for(f"import module {module}")
            if not ok:
                raise ImportError(f"Import of module {module} rejected by user.")
            import_cache_ok[module] = ok


    # elif event.startswith("object."):
    #     print(f"object.* event: {event} with args: {args}")


# sys.addaudithook(audit_hook)


def print_request_http11_style(request: httpx.Request):
    method = request.method
    path = request.url.path
    print(f"{method} {path} HTTP/1.1")
    for header, value in request.headers.items():
        print(f"{header}: {value}")
    print()  # Add a blank line after the headers for better readability


def print_response_http11_style(response: httpx.Response):
    status_code = response.status_code
    reason = response.reason_phrase
    print(f"HTTP/1.1 {status_code} {reason}")
    for header, value in response.headers.items():
        print(f"{header}: {value}")
    print()  # Add a blank line after the headers for better readability


with httpx.Client(
    event_hooks={
        "request": [print_request_http11_style],
        "response": [print_response_http11_style],
    }
) as client:
    response = client.get("https://httpbin.org/get")
    print(response.text)

for event, count in c.most_common():
    print(f"{event}: {count}")
