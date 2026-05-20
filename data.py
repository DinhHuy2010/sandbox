# from threading import Event, Thread
# from time import sleep
# from queue import Empty, Queue

# messages = Queue()
# stop = Event()


# def sender():
#     for i in range(5):
#         msg = f"Message {i}"
#         messages.put(msg)
#         print(f"Sent: {msg}")

#     stop.set()


# def receiver():
#     while not stop.is_set() or not messages.empty():
#         print("Waiting for messages...")
#         try:
#             msg = messages.get(timeout=2)
#         except Empty:
#             continue

#         print(f"Received: {msg}")
#         messages.task_done()
#         # sleep(1)


# r = Thread(target=receiver)
# r.start()

# sender()

# messages.join()
# r.join()

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


async def test():
    async with AsyncClient(
        mounts={"http://localhost:8000": ASGITransport(app=app)}
    ) as client:
        response = await client.get("http://localhost:8000/openapi.json")
        print(response.text)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test())
