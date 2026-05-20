import sys
from threading import Lock

lock = Lock()


class BaseHook:
    def __init__(self):
        self._lock = Lock()
        self._credits_used: float = 0
        self._enabled = True

    def add_to_credits(self, amount):
        with self._lock:
            self._credits_used += amount
            print(f"Credits used: {self._credits_used}")

    def _dispatch_on(self, event, args):
        if not self._enabled:
            return
        event = event.replace(".", "_")
        meth = getattr(self, f"on_dispatch_{event}", None)
        if meth is not None:
            meth(*args)

    def audit_hook(self, event, args):
        if not self._enabled:
            return
        self._dispatch_on(event, args)

    def tracer(self, frame, event, arg):
        if not self._enabled:
            return None
        self._dispatch_on(f"tracing.{event}", (frame, arg))
        return self.tracer

    def enable(self):
        with self._lock:
            self._enabled = True

    def disable(self):
        with self._lock:
            self._enabled = False


class MyHook(BaseHook):
    def on_dispatch_open(self, filename, mode, flags):
        print(f"File opened: {filename} with mode {mode}")
        in_binary = "b" in mode
        if in_binary:
            if "r" in mode:
                self.add_to_credits(0.5)
            elif "w" in mode:
                self.add_to_credits(1)
            elif "a" in mode:
                self.add_to_credits(0.75)
            elif "x" in mode:
                self.add_to_credits(1.25)
        else:
            if "r" in mode:
                self.add_to_credits(0.75)
            elif "w" in mode:
                self.add_to_credits(1.25)
            elif "a" in mode:
                self.add_to_credits(1)
            elif "x" in mode:
                self.add_to_credits(1.5)

    def on_dispatch_import(self, name, path, *_):
        print(f"Module imported: {name} from {path}")
        self.add_to_credits(1)

    def on_dispatch_tracing_line(self, frame, arg):
        print(f"Line executed: {frame.f_code.co_name} at {frame.f_lineno}")
        self.add_to_credits(0.01)


hook = MyHook()
sys.addaudithook(hook.audit_hook)
sys.settrace(hook.tracer)
import IPython, httpx

# sys.settrace(tracer)
IPython.embed()
hook.disable()
print(hook._credits_used)


# sys.settrace(None)
