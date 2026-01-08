import ctypes
import types
import traceback

# --- CPython C-API bindings (ctypes) ---
pythonapi = ctypes.pythonapi

PyThreadState_Get = pythonapi.PyThreadState_Get
PyThreadState_Get.restype = ctypes.c_void_p

PyFrame_New = pythonapi.PyFrame_New
PyFrame_New.argtypes = [ctypes.c_void_p, ctypes.py_object, ctypes.py_object, ctypes.py_object]
PyFrame_New.restype = ctypes.py_object


def make_fake_frame(*, filename="evil.py", funcname="ghost", firstlineno=666):
    # Make a real code object (in Python) and then mutate its metadata.
    # This avoids constructing a CodeObject via C (which is super version-fragile).
    def template():
        return 123

    code = template.__code__.replace(
        co_filename=filename,
        co_name=funcname,
        co_firstlineno=firstlineno,
    )

    tstate = PyThreadState_Get()
    globals_dict = {}  # can be any dict; affects how the frame prints/behaves in tools
    frame = PyFrame_New(tstate, code, globals_dict, None)
    return frame


def raise_with_forged_traceback():
    frame = make_fake_frame(filename="totally_real_module.py", funcname="banking_magic", firstlineno=9001)

    # In modern CPython, displayed line numbers come from code/line-table,
    # so co_firstlineno is what makes the "line 9001" show up reliably.
    tb = types.TracebackType(tb_next=None, tb_frame=frame, tb_lasti=0, tb_lineno=frame.f_lineno)

    raise RuntimeError("👻 forged frame via ctypes").with_traceback(tb)


if __name__ == "__main__":
    try:
        raise_with_forged_traceback()
    except Exception as e:
        print("".join(traceback.format_exception(type(e), e, e.__traceback__)))
