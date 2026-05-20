import asyncio
from pathlib import Path
from shutil import which
from typing import AsyncGenerator
from zlib import decompressobj

import fastapi
from fastapi.responses import StreamingResponse

app = fastapi.FastAPI()
GIT_BIN = which("git") or "/usr/bin/git"
REPOS_DIR = Path("~/downloaded_repos").expanduser().resolve()


def get_repo_path(repo_name: str) -> Path:
    # Ensure the target directory is a valid git repository
    path = REPOS_DIR / repo_name
    if not path.exists():
        raise fastapi.HTTPException(status_code=404, detail="Repository not found")
    return path


# ──────────────────────────────────────────────────────────────────────
# 1. THE DISCOVERY PHASE (info/refs) - REFIXED WITH STRICT PKT-LINE
# ──────────────────────────────────────────────────────────────────────
@app.get("/git/{repo_name}/info/refs")
async def git_info_refs(repo_name: str, service: str):
    """
    Handles initial discovery with flawless packet-line length encoding.
    """
    repo_path = get_repo_path(repo_name)

    if service not in ["git-upload-pack", "git-receive-pack"]:
        raise fastapi.HTTPException(status_code=400, detail="Unsupported git service")

    rpc_command = service.replace("git-", "")
    cmd = [GIT_BIN, rpc_command, "--stateless-rpc", "--advertise-refs", str(repo_path)]

    p = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await p.communicate()

    if p.returncode != 0:
        # logfire.error("Git ref advertisement failed", stderr=stderr.decode())
        raise fastapi.HTTPException(status_code=500, detail="Git plumbing failed")

    # --- BULLETPROOF PKT-LINE GENERATION ---
    # Line 1: Must be the service advertisement header terminated by a newline
    line1 = f"# service={service}\n".encode("utf-8")
    # Calculate exact byte length + 4 bytes for the hex prefix itself
    line1_len = f"{len(line1) + 4:04x}".encode("utf-8")

    # Line 2: The Git protocol requires a literal "0000" flush packet right after
    flush_packet = b"0000"

    # Stitch the protocol wrapper directly to the binary stdout payload
    response_body = line1_len + line1 + flush_packet + stdout

    # Logfire trace tracking for debugging the exact outgoing byte frames
    # logfire.debug(
    #     "Sending protocol response headers",
    #     expected_hex=line1_len.decode(),
    #     total_bytes=len(response_body)
    # )

    return fastapi.Response(
        content=response_body,
        media_type=f"application/x-{service}-advertisement",
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache", "Expires": "0"},
    )


# # ──────────────────────────────────────────────────────────────────────
# # 2. THE PACKFILE PHASE (upload-pack / receive-pack RPC) - FLUID STREAMING
# # ──────────────────────────────────────────────────────────────────────
# @app.post("/git/{repo_name}/{rpc_service}")
# async def git_rpc(repo_name: str, rpc_service: str, request: fastapi.Request):
#     """
#     Handles streaming packfile blocks using an internal queue to prevent loop starvation.
#     """
#     repo_path = get_repo_path(repo_name)

#     if rpc_service not in ["git-upload-pack", "git-receive-pack"]:
#         raise fastapi.HTTPException(status_code=400, detail="Invalid RPC service")

#     rpc_command = rpc_service.replace("git-", "")
#     cmd = [GIT_BIN, rpc_command, "--stateless-rpc", str(repo_path)]

#     p = await asyncio.create_subprocess_exec(
#         *cmd,
#         stdin=asyncio.subprocess.PIPE,
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE,
#     )

#     # d = decompress(
#     #     await request.body()
#     # )  # Force full body read to avoid stream conflicts
#     # stdout, stderr = await p.communicate(input=d)
#     # p.stdin.write(d)
#     # await p.stdin.drain()
#     # p.stdin.close()
#     async def decompress(d: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
#         decompressor = decompressobj()
#         async for chunk in d:
#             yield decompressor.decompress(chunk)
#         yield decompressor.flush()

#     async def send_to_stdin():
#         async for chunk in decompress(request.stream()):
#             p.stdin.write(chunk)
#             await p.stdin.drain()

#     async def stream_output() -> AsyncGenerator[bytes, None]:
#         while True:
#             chunk = await p.stdout.read(65536)  # Stream output in 64KB chunks
#             if not chunk:
#                 break
#             yield chunk

#     await send_to_stdin()
#     return StreamingResponse(
#         content=stream_output(),  # Stream output in 64KB chunks
#         media_type=f"application/x-{rpc_service}-result",
#         headers={"Cache-Control": "no-cache"},
#     )

# ──────────────────────────────────────────────────────────────────────
# 2. THE PACKFILE PHASE (upload-pack / receive-pack RPC) - CONCURRENT
# ──────────────────────────────────────────────────────────────────────
# @app.post("/git/{repo_name}/{rpc_service}")
# async def git_rpc(repo_name: str, rpc_service: str, request: fastapi.Request):
#     """
#     Handles streaming packfile blocks concurrently to prevent loop starvation.
#     """
#     repo_path = get_repo_path(repo_name)

#     if rpc_service not in ["git-upload-pack", "git-receive-pack"]:
#         raise fastapi.HTTPException(status_code=400, detail="Invalid RPC service")

#     rpc_command = rpc_service.replace("git-", "")
#     cmd = [GIT_BIN, rpc_command, "--stateless-rpc", str(repo_path)]

#     p = await asyncio.create_subprocess_exec(
#         *cmd,
#         stdin=asyncio.subprocess.PIPE,
#         stdout=asyncio.subprocess.PIPE,
#         stderr=asyncio.subprocess.PIPE,
#     )

#     # 1. Keep your streaming decompression pipeline intact
#     async def decompress(d: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
#         decompressor = decompressobj()
#         async for chunk in d:
#             yield decompressor.decompress(chunk)
#         yield decompressor.flush()

#     # 2. Write to stdin in the background
#     async def send_to_stdin():
#         try:
#             if p.stdin:
#                 async for chunk in decompress(request.stream()):
#                     p.stdin.write(chunk)
#                     # CRITICAL: Flushes OS pipeline data immediately, handing
#                     # loop execution priority back over to our stdout consumer
#                     await p.stdin.drain()
#                 # CRITICAL: Send EOF signal so the git utility knows input is complete
#                 p.stdin.close()
#         except Exception:
#             if p.stdin:
#                 p.stdin.close()

#     # Create an active concurrent background task for input stream processing
#     writer_task = asyncio.create_task(send_to_stdin())
#     await asyncio.sleep(0)  # Yield control to ensure the writer task starts before we read output

#     # 3. Yield output chunks safely
#     async def stream_output() -> AsyncGenerator[bytes, None]:
#         try:
#             if p.stdout:
#                 while True:
#                     chunk = await p.stdout.read(65536)  # Stream output in 64KB chunks
#                     if not chunk:
#                         break
#                     yield chunk

#             # Make sure the background stdin streaming process wraps up without leaks
#             await writer_task
#         finally:
#             # Safely shut down the operating system child process
#             await p.wait()


#     # Return immediately! FastAPI will consume stream_output() while
#     # send_to_stdin() runs concurrently in the background.
#     return StreamingResponse(
#         content=stream_output(),
#         media_type=f"application/x-{rpc_service}-result",
#         headers={"Cache-Control": "no-cache"},
#     )
# ──────────────────────────────────────────────────────────────────────
# 2. THE PACKFILE PHASE (upload-pack / receive-pack RPC) - DEADBAND PROOF
# ──────────────────────────────────────────────────────────────────────
@app.post("/git/{repo_name}/{rpc_service}")
async def git_rpc(repo_name: str, rpc_service: str, request: fastapi.Request):
    """
    Handles streaming packfile blocks using an internal queue to mix
    concurrent read/write cycles flawlessly without starvation or sudden dropouts.
    """
    repo_path = get_repo_path(repo_name)

    if rpc_service not in ["git-upload-pack", "git-receive-pack"]:
        raise fastapi.HTTPException(status_code=400, detail="Invalid RPC service")

    rpc_command = rpc_service.replace("git-", "")
    cmd = [GIT_BIN, rpc_command, "--stateless-rpc", str(repo_path)]

    p = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # An internal memory ring buffer to decouples Git's stdout from FastAPI's network layer
    chunk_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=128)

    # 1. Your custom streaming decompression pipeline
    # async def decompress(d: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
    #     decompressor = decompressobj()
    #     async for chunk in d:
    #         yield decompressor.decompress(chunk)
    #     yield decompressor.flush()

    # 2. Consume request body and pipe straight to Git's stdin
    async def send_to_stdin():
        try:
            if p.stdin:
                print("Feeding request body to Git's stdin...")  # Debug log to trace flow
                s = await request.stream()
                async for chunk in s:
                    print("Received chunk from request stream, writing to Git...")  # Debug log
                    p.stdin.write(chunk)
                    await (
                        p.stdin.drain()
                    )  # Yields loop control back so stdout can be read
                p.stdin.close()
        except Exception:
            if p.stdin:
                p.stdin.close()

    # 3. Drain Git's stdout straight into our async thread-safe queue
    async def read_from_stdout():
        try:
            if p.stdout:
                while True:
                    # Read in 32KB pieces to keep RAM clean
                    chunk = await p.stdout.read(32768)
                    if not chunk:
                        break
                    await chunk_queue.put(chunk)
        finally:
            # Send a Sentinel Token indicating Git has completely finished its execution
            await chunk_queue.put(None)

    # 4. An orchestrator task that runs BOTH streams simultaneously
    async def run_git_io_loop():
        # Executes input consumption and output gathering side-by-side
        await asyncio.gather(send_to_stdin(), read_from_stdout())
        await p.wait()

    # Fire up the concurrent background pipeline
    asyncio.create_task(run_git_io_loop())
    await asyncio.sleep(0)  # Yield control to ensure the IO loop starts before we read from the queue

    # 5. Generator that safely feeds FastAPI's StreamingResponse
    async def stream_from_queue() -> AsyncGenerator[bytes, None]:
        while True:
            print("Waiting for next chunk from Git...")  # Debug log to trace flow
            chunk = await chunk_queue.get()
            if chunk is None:  # Caught the sentinel token, exit cleanly!
                break
            yield chunk

    return StreamingResponse(
        content=stream_from_queue(),
        media_type=f"application/x-{rpc_service}-result",
        headers={"Cache-Control": "no-cache"},
    )
