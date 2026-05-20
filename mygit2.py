# # # git_server.py
# # import gzip
# # from pathlib import Path
# # import os
# # import subprocess

# # from fastapi import FastAPI, Request, HTTPException
# # from fastapi.responses import Response, StreamingResponse

# # app = FastAPI()

# # REPO_ROOT = Path("~/downloaded_repos").expanduser().resolve()
# # REPO_ROOT.mkdir(exist_ok=True)

# # ALLOWED_SERVICES = {
# #     "git-upload-pack": "upload-pack",
# #     "git-receive-pack": "receive-pack",
# # }


# # def pkt_line(data: bytes) -> bytes:
# #     return f"{len(data) + 4:04x}".encode() + data


# # def flush_pkt() -> bytes:
# #     return b"0000"


# # def repo_path(repo: str) -> Path:
# #     repo = repo.strip("/")
# #     if not repo.endswith(".git"):
# #         repo += ".git"

# #     path = (REPO_ROOT / repo).resolve()

# #     if not str(path).startswith(str(REPO_ROOT)):
# #         raise HTTPException(403, "Invalid repo path")

# #     if not path.exists():
# #         raise HTTPException(404, "Repository not found")

# #     return path

# # def run_git(
# #     service: str, repo: Path, body: bytes | None = None, advertise: bool = False
# # ):
# #     if service not in ALLOWED_SERVICES:
# #         raise HTTPException(403, "Service not allowed")

# #     git_cmd = ALLOWED_SERVICES[service]

# #     cmd = ["git", git_cmd, "--stateless-rpc"]

# #     if advertise:
# #         cmd.append("--advertise-refs")

# #     cmd.append(str(repo))

# #     proc = subprocess.Popen(
# #         cmd,
# #         stdin=subprocess.PIPE if body is not None else None,
# #         stdout=subprocess.PIPE,
# #         stderr=subprocess.PIPE,
# #         env={
# #             **os.environ,
# #             "GIT_HTTP_EXPORT_ALL": "1",
# #         },
# #     )

# #     stdout, stderr = proc.communicate(body)

# #     if proc.returncode != 0:
# #         print(f"Git command failed: {stderr}")
# #         raise HTTPException(500, stderr.decode(errors="replace"))

# #     return stdout

# # async def read_git_body(request: Request) -> bytes:
# #     body = await request.body()

# #     if request.headers.get("content-encoding", "").lower() == "gzip":
# #         body = gzip.decompress(body)

# #     return body

# # @app.get("/{repo:path}/info/refs")
# # async def info_refs(repo: str, service: str):
# #     if service not in ALLOWED_SERVICES:
# #         raise HTTPException(403, "Invalid service")

# #     path = repo_path(repo)

# #     advertised_refs = run_git(service, path, advertise=True)

# #     body = pkt_line(f"# service={service}\n".encode()) + flush_pkt() + advertised_refs

# #     return Response(
# #         body,
# #         media_type=f"application/x-{service}-advertisement",
# #         headers={
# #             "Cache-Control": "no-cache",
# #         },
# #     )


# # @app.post("/{repo:path}/git-upload-pack")
# # async def git_upload_pack(repo: str, request: Request):
# #     path = repo_path(repo)
# #     body = await read_git_body(request)

# #     output = run_git("git-upload-pack", path, body=body)

# #     return Response(
# #         output,
# #         media_type="application/x-git-upload-pack-result",
# #         headers={"Cache-Control": "no-cache"},
# #     )


# # @app.post("/{repo:path}/git-receive-pack")
# # async def git_receive_pack(repo: str, request: Request):
# #     path = repo_path(repo)
# #     body = await request.body()

# #     output = run_git("git-receive-pack", path, body=body)

# #     return Response(
# #         output,
# #         media_type="application/x-git-receive-pack-result",
# #         headers={"Cache-Control": "no-cache"},
# #     )


# # @app.post("/admin/create/{repo:path}")
# # async def create_repo(repo: str):
# #     repo = repo.strip("/")
# #     if not repo.endswith(".git"):
# #         repo += ".git"

# #     path = (REPO_ROOT / repo).resolve()

# #     if not str(path).startswith(str(REPO_ROOT)):
# #         raise HTTPException(403, "Invalid repo path")

# #     if path.exists():
# #         raise HTTPException(409, "Repository already exists")

# #     path.parent.mkdir(parents=True, exist_ok=True)

# #     proc = subprocess.run(
# #         ["git", "init", "--bare", str(path)],
# #         capture_output=True,
# #         text=True,
# #     )

# #     if proc.returncode != 0:
# #         raise HTTPException(500, proc.stderr)

# #     return {"created": str(path)}

# # git_server.py

import asyncio
import os
import zlib
import tempfile
from pathlib import Path
from typing import IO, AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

app = FastAPI()

# REPO_ROOT = Path("./repos").resolve()
REPO_ROOT = Path("~/downloaded_repos").expanduser().resolve()
# REPO_ROOT.mkdir(parents=True, exist_ok=True)

# SERVICES = {
#     "git-upload-pack": "upload-pack",
#     "git-receive-pack": "receive-pack",
# }


# def pkt_line(data: bytes) -> bytes:
#     return f"{len(data) + 4:04x}".encode() + data


# def flush_pkt() -> bytes:
#     return b"0000"


# def get_repo_path(repo: str) -> Path:
#     repo = repo.strip("/")

#     if not repo.endswith(".git"):
#         repo += ".git"

#     path = (REPO_ROOT / repo).resolve()

#     if not str(path).startswith(str(REPO_ROOT)):
#         raise HTTPException(403, "Invalid repository path")

#     if not path.exists():
#         raise HTTPException(404, "Repository not found")

#     return path


# def get_new_repo_path(repo: str) -> Path:
#     repo = repo.strip("/")

#     if not repo.endswith(".git"):
#         repo += ".git"

#     path = (REPO_ROOT / repo).resolve()

#     if not str(path).startswith(str(REPO_ROOT)):
#         raise HTTPException(403, "Invalid repository path")

#     return path


# async def iter_git_body(request: Request) -> AsyncIterator[bytes]:
#     encoding = request.headers.get("content-encoding", "").lower()

#     if encoding != "gzip":
#         async for chunk in request.stream():
#             if chunk:
#                 yield chunk
#         return

#     decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

#     async for chunk in request.stream():
#         if not chunk:
#             continue

#         data = decompressor.decompress(chunk)

#         if data:
#             yield data

#     tail = decompressor.flush()

#     if tail:
#         yield tail


# async def advertise_refs(service: str, repo: Path) -> bytes:
#     git_cmd = SERVICES.get(service)

#     if git_cmd is None:
#         raise HTTPException(403, "Service not allowed")

#     proc = await asyncio.create_subprocess_exec(
#         "git",
#         git_cmd,
#         "--stateless-rpc",
#         "--advertise-refs",
#         str(repo),
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE,
#         env={
#             **os.environ,
#             "GIT_HTTP_EXPORT_ALL": "1",
#         },
#     )

#     stdout, stderr = await proc.communicate()

#     if proc.returncode != 0:
#         raise HTTPException(
#             500,
#             stderr.decode(errors="replace"),
#         )

#     return pkt_line(f"# service={service}\n".encode()) + flush_pkt() + stdout


# async def stream_git_rpc(
#     service: str,
#     repo: Path,
#     request: Request,
# ) -> AsyncIterator[bytes]:
#     git_cmd = SERVICES.get(service)

#     if git_cmd is None:
#         raise HTTPException(403, "Service not allowed")

#     proc = await asyncio.create_subprocess_exec(
#         "git",
#         git_cmd,
#         "--stateless-rpc",
#         str(repo),
#         stdin=asyncio.subprocess.PIPE,
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE,
#         env={
#             **os.environ,
#             "GIT_HTTP_EXPORT_ALL": "1",
#         },
#     )

#     assert proc.stdin is not None
#     assert proc.stdout is not None
#     assert proc.stderr is not None

#     async def feed_stdin() -> None:
#         try:
#             async for chunk in iter_git_body(request):
#                 proc.stdin.write(chunk)
#                 await proc.stdin.drain()
#         except asyncio.CancelledError:
#             raise
#         finally:
#             try:
#                 proc.stdin.close()
#                 await proc.stdin.wait_closed()
#             except Exception:
#                 pass

#     async def log_stderr() -> None:
#         while True:
#             line = await proc.stderr.readline()

#             if not line:
#                 break

#             print(
#                 f"[{service}]",
#                 line.decode(errors="replace").rstrip(),
#             )

#     stdin_task = asyncio.create_task(feed_stdin())
#     stderr_task = asyncio.create_task(log_stderr())

#     try:
#         while True:
#             chunk = await proc.stdout.read(64 * 1024)

#             if not chunk:
#                 break

#             yield chunk

#         await stdin_task

#         returncode = await proc.wait()

#         if returncode != 0:
#             print(f"{service} exited with code {returncode}")

#     finally:
#         if not stdin_task.done():
#             stdin_task.cancel()

#         if not stderr_task.done():
#             stderr_task.cancel()

#         if proc.returncode is None:
#             proc.kill()
#             await proc.wait()


# @app.get("/{repo:path}/info/refs")
# async def info_refs(repo: str, service: str):
#     if service not in SERVICES:
#         raise HTTPException(403, "Invalid service")

#     path = get_repo_path(repo)
#     body = await advertise_refs(service, path)

#     return Response(
#         body,
#         media_type=f"application/x-{service}-advertisement",
#         headers={
#             "Cache-Control": "no-cache",
#             "Expires": "Fri, 01 Jan 1980 00:00:00 GMT",
#             "Pragma": "no-cache",
#         },
#     )


# @app.post("/{repo:path}/git-upload-pack")
# async def git_upload_pack(repo: str, request: Request):
#     path = get_repo_path(repo)

#     return StreamingResponse(
#         stream_git_rpc("git-upload-pack", path, request),
#         media_type="application/x-git-upload-pack-result",
#         headers={
#             "Cache-Control": "no-cache",
#             "Expires": "Fri, 01 Jan 1980 00:00:00 GMT",
#             "Pragma": "no-cache",
#         },
#     )


# @app.post("/{repo:path}/git-receive-pack")
# async def git_receive_pack(repo: str, request: Request):
#     path = get_repo_path(repo)

#     return StreamingResponse(
#         stream_git_rpc("git-receive-pack", path, request),
#         media_type="application/x-git-receive-pack-result",
#         headers={
#             "Cache-Control": "no-cache",
#             "Expires": "Fri, 01 Jan 1980 00:00:00 GMT",
#             "Pragma": "no-cache",
#         },
#     )


# @app.post("/admin/create/{repo:path}")
# async def create_repo(repo: str):
#     path = get_new_repo_path(repo)

#     if path.exists():
#         raise HTTPException(409, "Repository already exists")

#     path.parent.mkdir(parents=True, exist_ok=True)

#     proc = await asyncio.create_subprocess_exec(
#         "git",
#         "init",
#         "--bare",
#         str(path),
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE,
#     )

#     stdout, stderr = await proc.communicate()

#     if proc.returncode != 0:
#         raise HTTPException(
#             500,
#             stderr.decode(errors="replace"),
#         )

#     return {
#         "created": str(path),
#         "message": stdout.decode(errors="replace"),
#     }


# @app.get("/admin/repos")
# async def list_repos():
#     repos = []

#     for path in REPO_ROOT.rglob("*.git"):
#         if path.is_dir():
#             repos.append(str(path.relative_to(REPO_ROOT)))

#     return {"repos": repos}

SERVICES = {
    "git-upload-pack": "upload-pack",
    "git-receive-pack": "receive-pack",
}


def pkt_line(data: bytes) -> bytes:
    return f"{len(data) + 4:04x}".encode() + data


def flush_pkt() -> bytes:
    return b"0000"


def repo_path(repo: str, must_exist: bool = True) -> Path:
    repo = repo.strip("/")

    if not repo.endswith(".git"):
        repo += ".git"

    path = (REPO_ROOT / repo).resolve()

    if not str(path).startswith(str(REPO_ROOT)):
        raise HTTPException(403, "Invalid repo path")

    if must_exist and not path.exists():
        raise HTTPException(404, "Repository not found")

    return path


async def write_request_to_tempfile(request: Request) -> IO[bytes]:
    encoding = request.headers.get("content-encoding", "").lower()

    tmp = tempfile.SpooledTemporaryFile(max_size=128 * 1024 * 1024)  # 128 MB

    try:
        if encoding == "gzip":
            decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

            async for chunk in request.stream():
                if chunk:
                    data = decompressor.decompress(chunk)
                    if data:
                        tmp.write(data)

            tail = decompressor.flush()
            if tail:
                tmp.write(tail)

        else:
            async for chunk in request.stream():
                if chunk:
                    tmp.write(chunk)

        tmp.seek(0)
        return tmp

    except Exception:
        tmp.close()
        raise


async def advertise_refs(service: str, repo: Path) -> bytes:
    git_cmd = SERVICES[service]

    proc = await asyncio.create_subprocess_exec(
        "git",
        git_cmd,
        "--stateless-rpc",
        "--advertise-refs",
        str(repo),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "GIT_HTTP_EXPORT_ALL": "1"},
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise HTTPException(500, stderr.decode(errors="replace"))

    return pkt_line(f"# service={service}\n".encode()) + flush_pkt() + stdout


async def run_git_rpc_from_file(
    service: str,
    repo: Path,
    stdin_file: IO[bytes],
) -> AsyncIterator[bytes]:
    git_cmd = SERVICES[service]

    proc = await asyncio.create_subprocess_exec(
        "git",
        git_cmd,
        "--stateless-rpc",
        str(repo),
        stdin=stdin_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "GIT_HTTP_EXPORT_ALL": "1"},
    )

    assert proc.stdout is not None
    assert proc.stderr is not None

    async def drain_stderr() -> bytes:
        return await proc.stderr.read()

    stderr_task = asyncio.create_task(drain_stderr())

    try:
        while True:
            chunk = await proc.stdout.read(64 * 1024)

            if not chunk:
                break

            yield chunk

        returncode = await proc.wait()
        stderr = await stderr_task

        if returncode != 0:
            print(stderr.decode(errors="replace"))

    finally:
        if not stderr_task.done():
            stderr_task.cancel()

        try:
            stdin_file.close()
        except FileNotFoundError:
            pass


@app.get("/{repo:path}/info/refs")
async def info_refs(repo: str, service: str):
    if service not in SERVICES:
        raise HTTPException(403, "Invalid service")

    path = repo_path(repo)
    body = await advertise_refs(service, path)

    return Response(
        body,
        media_type=f"application/x-{service}-advertisement",
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Expires": "Fri, 01 Jan 1980 00:00:00 GMT",
        },
    )


@app.post("/{repo:path}/git-upload-pack")
async def git_upload_pack(repo: str, request: Request):
    path = repo_path(repo)
    body_file = await write_request_to_tempfile(request)

    return StreamingResponse(
        run_git_rpc_from_file("git-upload-pack", path, body_file),
        media_type="application/x-git-upload-pack-result",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/{repo:path}/git-receive-pack")
async def git_receive_pack(repo: str, request: Request):
    path = repo_path(repo)
    body_file = await write_request_to_tempfile(request)

    return StreamingResponse(
        run_git_rpc_from_file("git-receive-pack", path, body_file),
        media_type="application/x-git-receive-pack-result",
        headers={"Cache-Control": "no-cache"},
    )


@app.post("/admin/create/{repo:path}")
async def create_repo(repo: str):
    path = repo_path(repo, must_exist=False)

    if path.exists():
        raise HTTPException(409, "Repository already exists")

    path.parent.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "git",
        "init",
        "--bare",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise HTTPException(500, stderr.decode(errors="replace"))

    return {
        "created": str(path),
        "message": stdout.decode(errors="replace"),
    }
