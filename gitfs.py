from abc import ABC, abstractmethod

import fastapi

app = fastapi.FastAPI()


class GenericDirectoryLister(ABC):
    @abstractmethod
    def list_directory(self, path: str) -> list[str]: ...


class SimpleDirectoryLister(GenericDirectoryLister):
    def list_directory(self, path: str) -> list[str]:
        # For demonstration purposes, return a static list of files and directories.
        if path == "/":
            return ["file1.txt", "file2.txt", "subdir/"]
        elif path == "/subdir/":
            return ["file3.txt", "file4.txt"]
        else:
            return []

    def read_file(self, path: str) -> str:
        # For demonstration purposes, return a static file content.
        if path == "/file1.txt":
            return "This is the content of file1.txt."
        elif path == "/file2.txt":
            return "This is the content of file2.txt."
        elif path == "/subdir/file3.txt":
            return "This is the content of file3.txt."
        elif path == "/subdir/file4.txt":
            return "This is the content of file4.txt."
        else:
            return "File not found."

    def head_file(self, path: str) -> dict:
        # For demonstration purposes, return static file metadata.
        if path in [
            "/file1.txt",
            "/file2.txt",
            "/subdir/file3.txt",
            "/subdir/file4.txt",
        ]:
            return {
                "Content-Length": str(len(self.read_file(path))),
                "Content-Type": "text/plain",
            }
        else:
            return {"Content-Length": "0", "Content-Type": "text/plain"}

    def is_directory(self, path: str) -> bool:
        # For demonstration purposes, return True for directories and False for files.
        return path.endswith("/")


def generic_directory_tree_html(gdl: GenericDirectoryLister, path: str) -> str:
    """
    Generate a simple HTML page for a directory listing.

    Args:
        path (str): The path of the directory being listed.
        listing (list[str]): A list of file and directory names in the directory.

    Returns:
        str: An HTML string representing the directory listing.
    """
    listing = gdl.list_directory(path)
    title = f"Directory listing for {path}"
    html = f"<html><head><title>{title}</title></head><body>"
    html += f"<h1>Directory listing for {path}</h1>"
    html += "<ul>"
    if path != "/":
        parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
        html += f'<li><a href="{parent_path}">.. (parent directory)</a></li>'

    for item in listing:
        html += f'<li><a href="{item}">{item}</a></li>'
    html += "</ul></body></html>"
    return html


gdl = SimpleDirectoryLister()


@app.api_route(
    "/{path:path}",
    response_class=fastapi.responses.HTMLResponse,
    methods=["GET", "HEAD"],
)
def read_root(path: str, request: fastapi.Request):
    if gdl.is_directory(path):
        return generic_directory_tree_html(gdl, path)
    else:
        if request.method == "HEAD":
            headers = gdl.head_file(path)
            return fastapi.responses.Response(content="", headers=headers)
        else:
            content = gdl.read_file(path)
            headers = gdl.head_file(path)
            return fastapi.responses.Response(content=content, headers=headers)


