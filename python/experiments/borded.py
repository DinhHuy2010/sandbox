# pyright: strict

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Annotated, TypeAlias

from pydantic import AfterValidator, BaseModel, Field, validate_call

EscapeHTML = AfterValidator(escape)


def unescape_attr(attr: str) -> str:
    if attr in {"class_"}:
        return "class"
    return attr


HTMLText: TypeAlias = Annotated[str, EscapeHTML]
EscapedAttributeValue: TypeAlias = Annotated[str, EscapeHTML]
ElementNode: TypeAlias = "HTMLTextElement | RawHTMLElement | Element | BaseElement"


class BaseElement(BaseModel):
    def to_html(self, indent: int = 0) -> str:
        raise NotImplementedError("Subclasses must implement to_html()")

    __str__ = to_html


class HTMLTextElement(BaseElement):
    text: HTMLText

    def to_html(self, indent: int = 0) -> str:
        return self.text


class RawHTMLElement(BaseElement):
    raw: str

    def to_html(self, indent: int = 0) -> str:
        return self.raw


class Element(BaseElement):
    tag: str
    content: list[ElementNode] | None = Field(default=None)
    attrs: dict[str, EscapedAttributeValue]

    def to_html(self, indent: int = 0) -> str:
        indent_str = "  " * indent
        attrs_str = "".join(
            f' {unescape_attr(attr)}="{value}"' for attr, value in self.attrs.items()
        )

        if self.content is None:
            return f"{indent_str}<{self.tag}{attrs_str} />"

        # Detect if all children are text (inline mode)
        is_inline = all(
            isinstance(item, (HTMLTextElement, RawHTMLElement)) for item in self.content
        )

        if is_inline:
            inner_html = "".join(item.to_html(0) for item in self.content)
            return f"{indent_str}<{self.tag}{attrs_str}>{inner_html}</{self.tag}>"

        # Block mode
        inner_html = "\n".join(item.to_html(indent + 1) for item in self.content)
        return f"{indent_str}<{self.tag}{attrs_str}>\n{inner_html}\n{indent_str}</{self.tag}>"


@dataclass
class TagFactory:
    tag: str
    default_attrs: dict[str, str]

    @validate_call
    def __call__(
        self,
        content: str | BaseElement | list[str | BaseElement] | None = None,
        *contents: str | BaseElement,
        extra_attrs: dict[str, str] | None = None,
        **attrs: EscapedAttributeValue,
    ) -> Element:
        all_attrs = {**self.default_attrs, **attrs, **(extra_attrs or {})}
        items: list[ElementNode] = []
        for item in (content, *contents):
            if item is None:
                continue
            elif isinstance(item, str):
                if self.tag in {"script", "style"}:
                    items.append(RawHTMLElement(raw=item))
                else:
                    items.append(HTMLTextElement(text=item))
            elif isinstance(item, BaseElement):
                items.append(item)
            else:
                raise TypeError(f"Invalid content type: {type(item)}")
        items = items if items else None  # type: ignore
        return Element(tag=self.tag, content=items, attrs=all_attrs)

    def __getitem__(self, attrs: dict[str, str]) -> "TagFactory":
        new_attrs = {**self.default_attrs, **attrs}
        return TagFactory(tag=self.tag, default_attrs=new_attrs)


def build_for_tag(tag: str, **default_attrs: str) -> TagFactory:
    return TagFactory(tag=tag, default_attrs=default_attrs)


class MetaTree(type):
    def __getattr__(cls, tag: str) -> TagFactory:
        return build_for_tag(tag)

    __getitem__ = __getattr__  # Allow Tree["div"] as well as Tree.div


class Tree(metaclass=MetaTree):
    pass


html = Tree.html(
    Tree.head(
        Tree.title("Example Page"),
        Tree.meta(
            charset="UTF-8",
            extra_attrs={"http-equiv": "X-UA-Compatible", "content": "IE=edge"},
        ),
        Tree.script("alert('Hello, world!');"),
    ),
    Tree.body(
        Tree.h1("Welcome to the Example Page"),
        Tree.p("This is a simple example of using the Tree class."),
        Tree.a("Click here", href="https://example.com/"),
        Tree.table(
            Tree.tr(
                Tree.td("Row 1, Cell 1"),
                Tree.td("Row 1, Cell 2"),
            ),
            Tree.tr(
                Tree.td("Row 2, Cell 1"),
                Tree.td("Row 2, Cell 2"),
            ),
        ),
    ),
)
print(html.model_dump_json(indent=2))
