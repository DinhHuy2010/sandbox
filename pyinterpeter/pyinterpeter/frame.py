from __future__ import annotations

from ast import AST
from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Frame:
    id: UUID = field(init=False, default_factory=uuid4)
    localvars: dict[str, object] = field(repr=False)
    globalvars: dict[str, object] = field(repr=False)
    builtins: dict[str, object] = field(repr=False)
    node: AST | None = field(repr=False)
    lineno: int = field(repr=False)

    prev: Frame | None = field(repr=False)

    @classmethod
    def new(cls, globalvars: dict[str, object], builtins: dict[str, object]) -> Frame:
        return cls(globalvars, globalvars, builtins, None, 0, None)

    def next(self, node: AST) -> Frame:
        lineno = getattr(node, "lineno", None)
        return Frame(
            {},
            self.globalvars,
            self.builtins,
            node,
            lineno or self.lineno + 1,
            self,
        )

    def format_id(self):
        return f"#{self.id.hex}"
