import sys
from struct import pack

_ = 0
in_files_section = False
fit = sys.stdin.buffer
for line in fit:
    line = line.rstrip(b"\n")
    if not line:
        continue
    if line == b"[Files]":
        in_files_section = True
        continue
    elif line == b"[End]":
        break
    if in_files_section:
        try:
            timestamp, entry_type, size, relative_path = line.split(b"\t")
        except ValueError:
            continue
        sys.stdout.buffer.write(pack("<Q", int(timestamp)))
        sys.stdout.buffer.write(entry_type)
        sys.stdout.buffer.write(pack("<Q", int(size)))
        sys.stdout.buffer.write(relative_path)
        sys.stdout.buffer.write(b"\x00")
