# from collections.abc import Callable, Iterable

# # from re import A
# from typing import Any


# class BreakLoop(Exception):
#     pass


# class ContinueLoop(Exception):
#     pass


# def for_loop[T](
#     iterable: Iterable[T],
#     func: Callable[[T], None],
#     else_block: Callable[[], None] = None,
# ) -> None:
#     for item in iterable:
#         try:
#             func(item)
#         except BreakLoop:
#             break
#         except ContinueLoop:
#             continue
#     else:
#         if else_block is not None:
#             else_block()


# def while_loop(
#     condition: Callable[[], bool],
#     func: Callable[[], None],
#     else_block: Callable[[], None] = None,
# ) -> None:
#     while condition():
#         try:
#             func()
#         except BreakLoop:
#             break
#         except ContinueLoop:
#             continue
#     else:
#         if else_block is not None:
#             else_block()


# def error(
#     exc: BaseException | type[BaseException], from_exc: BaseException | None = None
# ) -> None:
#     raise exc from from_exc


# def condition[T, F](x: bool, true: Callable[[], T], false: Callable[[], F]) -> T | F:
#     if x:
#         return true()
#     else:
#         return false()


# def multiple_conditions(
#     *conditions: tuple[bool, Callable[[], Any]] | Callable[[], Any],
# ) -> Any:
#     for condition in conditions:
#         if callable(condition):
#             return condition()
#         else:
#             cond, action = condition
#             if cond:
#                 return action()


# def _hash_version():
#     import hashlib
#     from io import BytesIO

#     with open(__file__, "rb") as f:
#         file_content = f.read()

#     blob = BytesIO()
#     blob.write(f"blob {len(file_content)}\0".encode("utf-8"))
#     blob.write(file_content)
#     blob.seek(0)
#     sha1 = hashlib.sha1(usedforsecurity=False)
#     sha1.update(blob.read())
#     return sha1.hexdigest()


# PRECISE_VERSION = _hash_version()
# del _hash_version

# multiple_conditions(
#     (False, lambda: print("This will not be printed.")),
#     (True, lambda: print("This will be printed.")),
#     lambda: print("This will not be printed because the previous condition was True."),
# )

# # i = 0

# # def c():
# #     return i < 5

# # def b():
# #     global i
# #     print("This will run indefinitely unless BreakLoop is raised.")
# #     i += 1

# # while_loop(
# #     condition=c,
# #     func=b,
# #     else_block=lambda: print("This will never be printed."),
# # )

# print(f"Precise version hash: {PRECISE_VERSION}")


import datetime
from io import BytesIO
from os import getcwd
import struct

import scandir_rs

# p = scandir_rs.Walk(".",  return_type=scandir_rs.ReturnType.Ext)
# print(p)
# s = 0
# while p.busy:
#     results = p.entries(only_new=True)
#     for entry in results:
#         print(
#             f"{entry.st_dev}:{entry.st_ino} -> {entry.path} ({stat.filemode(entry.st_mode)})"
#         )
#     # s += len(results)
#     sleep(0.1)


# def encode_stats(stats: scandir_rs.Statistics):
#     return struct.pack("Q Q")


def unix(timestamp: datetime.datetime | None) -> float:
    if timestamp is None:
        return 0.0
    return timestamp.timestamp()


p = scandir_rs.Scandir(getcwd(), return_type=scandir_rs.ReturnType.Ext)
p.start()
p.join()
entries, _ = p.collect()
print("Done scanning.")
b = BytesIO()
b.write(b"funny2scandir\x00\x00")
b.write(struct.pack("Q", len(entries)))
for entry in entries:
    if entry.is_file:
        with open(entry.path, "rb") as f:
            content = f.read()
        b.write(struct.pack("I", len(entry.path)))
        b.write(entry.path.encode("utf-8"))
        b.write(struct.pack("Q", entry.st_mode))
        b.write(struct.pack("Q", entry.st_size))
        b.write(struct.pack("F", unix(entry.st_mtime)))
        b.write(struct.pack("F", unix(entry.st_atime)))
        b.write(struct.pack("F", unix(entry.st_ctime)))
        b.write(struct.pack("Q", entry.st_ino))
        b.write(struct.pack("Q", entry.st_dev))
        b.write(content)
p = len(b.getvalue())
with open("funny2scandir.bin", "wb") as f:
    f.write(b.getvalue())
# p.join()
# print("Done scanning.")
# print("Duration:", p.duration)
# print("Total entries found:", p.results_cnt())
