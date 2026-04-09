from typing import Any, Iterable

from fastapi import FastAPI, WebSocket
from fastapi.responses import PlainTextResponse

app = FastAPI()


@app.get("/", response_class=PlainTextResponse)
def read_root() -> str:
    return "Hello, World!"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message received: {data}")

@app.get("/events/stream")
def event_stream() -> Iterable[Any]:
    for _ in range(5):
        yield {"message": "Hello, World!"}
