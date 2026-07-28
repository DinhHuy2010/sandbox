# ruff: noqa
# fmt: off
# type: ignore

ceaser = lambda t, s: "".join((chr((ord(c) - (ord("A") if c.isupper() else ord("a")) + s) % 26 + (ord("A") if c.isupper() else ord("a"))) if c.isalpha() else c) for c in t)
unceaser = lambda t, s: ceaser(t, -s)
print(ceaser("Hello, World!", 3))  # Output: "Khoor, Zruog!"
print(unceaser("Khoor, Zruog!", 3))  # Output: "Hello, World!"
