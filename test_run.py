import os
from pathlib import Path
from subprocess import PIPE
import tempfile

import anyio
from anyio.streams.text import TextReceiveStream


async def stream_command_anyio(command: list[str], cwd=None, env=None):
    """
    Spawns a shell process and yields (stream_type, line) in real-time.
    stream_type will be either 'stdout' or 'stderr'.
    """
    # 1. Open the process with separate PIPEs using AnyIO
    async with await anyio.open_process(
        command,
        stdout=PIPE,
        stderr=PIPE,
        cwd=cwd,
        env={**os.environ, **(env or {})},
    ) as process:
        # 2. Wrap raw byte pipes into UTF-8 text streams
        stdout_text = TextReceiveStream(process.stdout)
        stderr_text = TextReceiveStream(process.stderr)

        # 3. Create a memory object stream to act as our async queue
        send_stream, receive_stream = anyio.create_memory_object_stream()

        # 4. Helper worker to read a text stream and push lines into the channel
        async def stream_reader(text_stream, stream_type: str):
            async with send_stream:  # Closes clone when worker finishes
                async for chunk in text_stream:
                    # Handle incoming data line-by-line
                    for line in chunk.splitlines(keepends=True):
                        await send_stream.send((stream_type, line))

        # 5. Run both readers concurrently in a task group
        async with anyio.create_task_group() as tg:
            tg.start_soon(stream_reader, stdout_text, "stdout")
            tg.start_soon(stream_reader, stderr_text, "stderr")

            # 6. Yield lines to the consumer as they arrive in the memory channel
            async with receive_stream:
                async for stream_type, line in receive_stream:
                    yield stream_type, line

        # 7. Wait for the process to exit completely
        await process.wait()


async def uv(*args, cwd=None, env=None):
    command = ["uv"] + list(args)
    async for stream_type, line in stream_command_anyio(command, cwd=cwd, env=env):
        print(f"[{stream_type}] {line}", end="")  # line already has newline


async def main():
    requirements = Path("EXAMPLE_requirements.txt").resolve()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        print("Creating virtual environment...")
        await uv("venv", cwd=tmp)
        print("Installing requirements...")
        await uv(
            "pip",
            "install",
            "-r",
            str(requirements),
            "--verbose",
            "--no-cache",
            cwd=tmp,
            env={
                "VIRTUAL_ENV": str(tmp / "venv"),
                "UV_INDEX_URL": "http://localhost:8000/simple/",
            },
        )


if __name__ == "__main__":
    anyio.run(main)
