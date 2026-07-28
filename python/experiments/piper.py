from contextvars import ContextVar
from hashlib import sha256
from secrets import token_hex
from fastapi import FastAPI

# Create a context variable that is automatically isolated to the current thread/coroutine
_current_session: ContextVar["PipeSession"] = ContextVar(
    "current_session", default=None
)


class PipeSession:
    def __init__(self, token, data, source):
        self._token = token
        self.data = data
        self.source = source
        self.response = {"state": "pending"}

    def get_state(self):
        return self.response.get("state", "pending")

    # ... Keep your existing mark_done / encode_uri methods exactly as they were ...
    def mark_accepted(self):
        self.response["state"] = "accepted"

    def mark_result(self, result):
        self.response["result"] = result

    def mark_done(self):
        self.response["state"] = "done"

    def encode_uri(self):
        s = sha256(self._token.encode(), usedforsecurity=False).hexdigest()
        return f"<urn:piper:pipe:{self.get_state()}:{s}>"


class Pipe:
    # A property that safely fetches the context-isolated session
    @property
    def session(self) -> PipeSession:
        sess = _current_session.get()
        if sess is None:
            raise RuntimeError("No pipe session active in this context!")
        return sess

    @classmethod
    def call(cls, **data):
        return invoke_pipe(cls, **data, source=f"pipe.{cls.__name__}")

    @classmethod
    def run(cls):
        pass


def invoke_pipe(pipe_cls, source=None, **data):
    session = PipeSession(token=token_hex(), data=data, source=source)

    # Set the variable for this context and keep the token to reset it later
    ctx_token = _current_session.set(session)
    try:
        # Create an instance to access the session property locally
        instance = pipe_cls()
        instance.run()
    except Exception as e:
        session.response["state"] = "error"
        session.response["error"] = {"type": type(e).__name__, "message": str(e)}
    finally:
        # Safely restore previous context state (supports nesting!)
        _current_session.reset(ctx_token)

    return session.response


class AddPipe(Pipe):
    def run(self):  # Note: instance method now
        print(self.session.encode_uri())
        self.session.mark_accepted()
        a = self.session.data.get("a", 0)
        b = self.session.data.get("b", 0)
        self.session.mark_result(a + b)
        self.session.mark_done()


def expose_http(pipe, host=None, port=None, endpoint="/rpc"):
    app = FastAPI(openapi_url=None, docs_url=None)

    @app.post(endpoint)
    async def rpc_endpoint(payload: dict):
        return invoke_pipe(pipe, source="http", **payload)

    if host is None and port is None:
        return app
    else:
        import uvicorn

        uvicorn.run(app, host=host or "127.0.0.1", port=port or 8000)


def expose_multi_http(pipes, host=None, port=None):
    app = FastAPI(openapi_url=None, docs_url=None)

    for pipe in pipes:
        endpoint = f"/rpc/{pipe.__name__.lower()}"  # e.g., /rpc/addpipe

        @app.post(endpoint)
        async def rpc_endpoint(
            payload: dict, pipe=pipe
        ):  # Capture current pipe in closure
            return invoke_pipe(pipe, source="http", **payload)

    if host is None and port is None:
        return app
    else:
        import uvicorn

        uvicorn.run(app, host=host or "127.0.0.1", port=port or 8000)


# Look ma, clean syntax!
x = AddPipe.call(a=5, b=10)
print(x["result"])  # Output: 15
expose_http(AddPipe, host="127.0.0.1", port=9999)
