from asyncio import CancelledError
from enum import Enum
from io import BytesIO
import json
from random import randint
from traceback import print_exc
from typing import IO, Any
from uuid import UUID


from websockets import Request, Response
from websockets.asyncio.server import serve, ServerConnection


class Payload(Enum):
    MOVE = b"\xfd\xa5\xdb\xf1"
    CLICK = b"8I\x95\x10"
    SCROLL = b"\rQ\xc7R"


MAGIC = b"\x92\xe3\x80R\xeaU#\xc6\x98\x18\xde^\xad\xfc!\x15"
FLUSH = b"\x00\x00\x00\x00"

BATCH_MAGIC = b"\xdd\x85\x1dBi\x19\xb1\xe8j\xeeUz9\xac\xe7\xb9\xff4\xb9\xe7\xa3]3\xee\x064\xe9i\x91R\xbd="


def decode_number(x: bytes) -> int:
    return int.from_bytes(x, "big")


def parse_sender_batch_payload(message: IO[bytes]) -> list[dict[str, Any]]:
    f = message

    d = []
    if f.read(len(BATCH_MAGIC)) != BATCH_MAGIC:
        raise ValueError("Invalid batch magic bytes")
    while True:
        p = parse_sender_payload_single(f)
        d.append(p)
        if not p:
            break
    return d


def parse_sender_payload_single(message: IO[bytes]) -> dict[str, Any]:
    f = message

    def read_number(n=8):
        return decode_number(f.read(n))

    d = {}
    magic = f.read(len(MAGIC))
    if not magic:
        return {}
    if magic != MAGIC:
        raise ValueError("Invalid magic bytes")
    action = f.read(4)
    try:
        action = Payload(action)
    except ValueError:
        raise ValueError("Invalid action payload")
    d["action"] = action.name.lower()
    uuid = read_number()
    d["uuid"] = uuid
    timestamp_ms = read_number()
    d["timestamp_ms"] = timestamp_ms
    match action:
        case Payload.MOVE:
            d["x"] = read_number()
            d["y"] = read_number()
        case Payload.CLICK:
            d["x"] = read_number()
            d["y"] = read_number()
            d["button"] = read_number(1)
            d["pressed"] = bool(read_number(1))
        case Payload.SCROLL:
            d["x"] = read_number()
            d["y"] = read_number()
            d["dx"] = read_number()
            d["dy"] = read_number()
    if f.read(len(FLUSH)) != FLUSH:
        raise ValueError("Invalid flush bytes")
    return d


def parse_sender_payload(message: bytes) -> dict[str, Any] | list[dict[str, Any]]:
    if message.startswith(BATCH_MAGIC):
        return parse_sender_batch_payload(BytesIO(message))
    elif message.startswith(MAGIC):
        return parse_sender_payload_single(BytesIO(message))
    else:
        raise ValueError("Invalid message format")


async def handler(websocket: ServerConnection):
    print(f"Client connected: {websocket.remote_address}")
    # await websocket.send("Hello from the WebSocket server!")
    await websocket.ping("ping")
    await websocket.send(
        json.dumps(
            {"status": "connected", "message": "Welcome to the WebSocket server!"}
        )
    )
    try:
        async for message in websocket:
            print(f"Received message from client: {message}")
            meg = parse_sender_payload(message)
            try:
                print(f"Parsed message: {meg}")
            except ValueError:
                print(f"Failed to parse message (payload was: {message})")
            if randint(0, 10) < 2:
                await websocket.send(
                    f"Hello from the WebSocket server! You said: {message}"
                )
            # await websocket.pong()
    except Exception:
        print_exc()
    finally:
        print(f"Client disconnected: {websocket.remote_address}")


def on_response(websocket: ServerConnection, request: Request, response: Response):
    print(f"Received response from client: {request.serialize()}")
    # print("Sec-WebSocket-Key:", request.headers.get("Sec-WebSocket-Key"))


async def main():
    async with serve(
        handler,
        "localhost",
        # "0.0.0.0",
        8765,
        process_response=on_response,
        origins=["local://senderpy.localhost"],
    ) as server:
        print("WebSocket server started on ws://localhost:8765")
        try:
            await server.serve_forever()
        except CancelledError:
            print("WebSocket server is shutting down...")
            server.close()
            await server.wait_closed()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
