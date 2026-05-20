import fastapi
from app.simple_reader import create_context

app = fastapi.FastAPI()
context = create_context()

@app.get("/", response_class=fastapi.responses.PlainTextResponse)
def read_root():
    return "Hello, World!"


