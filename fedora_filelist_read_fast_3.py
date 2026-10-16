# ruff: noqa
import sys

in_files_section = False
write = sys.stdout.buffer.write
f, d = b"file", b"directory"
fheader = b"[Files]"
endheader = b"[End]"
for line in sys.stdin.buffer:
    line = line.rstrip(b"\n")
    if not line:
        continue
    if line == fheader:
        in_files_section = True
        continue
    elif line == endheader:
        break
    elif in_files_section:
        try:
            timestamp, entry_type, size, relative_path = line.split(b"\t")
        except ValueError:
            continue
        write((f if entry_type == b"f" else d) + (b" " + relative_path + b"\n"))
