from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, RootModel

from wblangs import WikibaseLanguage, WikidataConnectedWikis


class Rank(str, Enum):
    deprecated = "deprecated"
    normal = "normal"
    preferred = "preferred"


class ValueType(str, Enum):
    VALUE = "value"
    SOMEVALUE = "somevalue"
    NOVALUE = "novalue"


class PropertyRef(BaseModel):
    id: str | None = Field(None, description="The ID of the Property")
    data_type: str | None = Field(None, description="The data type of the Property")


class Value(BaseModel):
    content: Any | None = Field(
        None, description='The value, if type == "value", otherwise omitted'
    )
    type: ValueType | None = Field(None, description="The value type")


class Snak(BaseModel):
    property: PropertyRef | None = None
    value: Value | None = None


class Reference(BaseModel):
    hash: str | None = Field(None, description="Hash of the Reference")
    parts: list[Snak] = Field(
        default_factory=list[Snak], description="The Snaks of the Reference"
    )


class Statement(BaseModel):
    id: str | None = Field(
        None, description="The globally unique identifier for this Statement"
    )
    rank: Rank = Field(default=Rank.normal)
    property: PropertyRef | None = None
    value: Value | None = None
    qualifiers: list[Snak] = Field(default_factory=list[Snak])
    references: list[Reference] = Field(default_factory=list[Reference])


class Sitelink(BaseModel):
    title: str
    badges: list[str] = Field(default_factory=list[str])
    url: str | None = None


class Labels(RootModel[dict[WikibaseLanguage, str]]):
    root: dict[WikibaseLanguage, str]


class Descriptions(Labels):
    pass


class Aliases(RootModel[dict[WikibaseLanguage, list[str]]]):
    root: dict[WikibaseLanguage, list[str]]


class Item(BaseModel):
    id: str | None = None
    type: Literal["item"] = "item"
    labels: Labels | None = None
    descriptions: Descriptions | None = None
    aliases: Aliases | None = None
    sitelinks: dict[WikidataConnectedWikis, Sitelink] | None = None
    statements: dict[str, list[Statement]] | None = None


class Property(BaseModel):
    id: str | None = None
    type: Literal["property"] = "property"
    data_type: str
    labels: Labels | None = None
    descriptions: Descriptions | None = None
    aliases: Aliases | None = None
    statements: dict[str, list[Statement]] | None = None
