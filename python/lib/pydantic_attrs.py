# pyright: strict

from __future__ import annotations

from typing import Annotated, Any, Callable, Literal, reveal_type

import attrs
import pydantic
from annotated_types import Gt, Lt


def validate_via_pydantic(config: pydantic.ConfigDict | None = None):
    def validator(self: Any, field: attrs.Attribute[Any], value: Any) -> None:
        if field.metadata.get("no_pydantic_validation", False):
            return
        conf = config.copy() if config else pydantic.ConfigDict()
        conf |= {"strict": True}
        adapter: pydantic.TypeAdapter[Any] = pydantic.TypeAdapter(
            field.type,
            config=pydantic.ConfigDict(**conf),
        )
        adapter.validate_python(value)

    return validator


def _convert_factory(
    config: pydantic.ConfigDict | None,
) -> Callable[[attrs.Attribute[Any], Any], Any]:
    def converter(value: Any, field: attrs.Attribute[Any]) -> Any:
        if field.metadata.get("no_pydantic_conversion", False):
            return value
        conf = config.copy() if config else pydantic.ConfigDict()
        adapter: pydantic.TypeAdapter[Any] = pydantic.TypeAdapter(
            field.type,
            config=pydantic.ConfigDict(**conf),
        )
        return adapter.validate_python(value)

    return converter


def convert_via_pydantic(config: pydantic.ConfigDict | None = None):
    return attrs.Converter(_convert_factory(config), takes_field=True)


def setattr_pydantic_hook(
    type: Literal["convert", "validate"], config: pydantic.ConfigDict | None = None
) -> Callable[[Any, attrs.Attribute[Any], Any], Any]:
    def on_setattr_hook(self: Any, field: attrs.Attribute[Any], value: Any) -> Any:
        if type == "validate":
            v = validate_via_pydantic(config)
            v(self, field, value)
            return value
        elif type == "convert":
            c = _convert_factory(config)
            return c(field, value)
        else:
            raise ValueError(f"Unknown type: {type}")

    return on_setattr_hook


@attrs.define(on_setattr=setattr_pydantic_hook("convert"))
class Person:
    name: str
    age: int
    age2: Annotated[int | None, Gt(18), Lt(150)] = None


def main() -> None:
    try:
        print(Person("Test", 1, age2="17"))  # type: ignore
    except pydantic.ValidationError as exc:
        for err in exc.errors():
            print(err)
    reveal_type(Person("Test", 20, age2="19").age2)  # type: ignore


if __name__ == "__main__":
    main()
