import sys

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
        print(f"{'file' if entry_type == b'f' else 'directory'} {relative_path.decode()}")
