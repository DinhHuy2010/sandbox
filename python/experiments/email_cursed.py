# pyright: strict


class HostDomain:
    def __init__(self, parts: str | tuple[str, ...]) -> None:
        if isinstance(parts, str):
            self.parts = (parts,)
        else:
            self.parts = parts

    def __str__(self):
        return ".".join(self.parts)

    def __getattr__(self, name: str):
        return HostDomain(self.parts + (name,))


class EmailWithName:
    def __init__(self, name: str) -> None:
        self.name = name
        self.domain = HostDomain(())

    def __getattr__(self, name: str):
        n = EmailWithName(self.name)
        n.domain = getattr(self.domain, name)
        return n

    def __str__(self):
        return f"{self.name}@{self.domain}"


class EmailName:
    def __init__(self, name: str) -> None:
        self.name = name

    def __matmul__(self, other: HostDomain) -> str:
        return f"{self.name}@{other}"

    @property
    def at(self) -> EmailWithName:
        return EmailWithName(self.name)


someone = EmailName("someone")
example = HostDomain("example")
print(example.com)  # example.com
print(example.co.uk)  # example.co.uk
print(someone@example.com)  # fmt: off
print(someone.at.example.com)  # fmt: off
