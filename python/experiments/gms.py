from __future__ import annotations

from pydantic import UUID4, AwareDatetime, BaseModel, Field, JsonValue


class Entity(BaseModel):
    uid: UUID4 = Field(frozen=True)


class EntityForwardRef(BaseModel):
    refercend_uid: UUID4 = Field(frozen=True)


class Object(Entity):
    data: JsonValue


class Property(Entity):
    name: str


class Relation(Entity):
    subject: EntityForwardRef
    property: EntityForwardRef
    object: EntityForwardRef
    created_at: AwareDatetime
    misc: JsonValue


class GraphStore:
    def __init__(self):
        self.objects: dict[UUID4, Object] = {}
        self.properties: dict[UUID4, Property] = {}
        self.relations: dict[UUID4, Relation] = {}

    def add_object(self, obj: Object):
        self.objects[obj.uid] = obj

    def add_property(self, prop: Property):
        self.properties[prop.uid] = prop

    def add_relation(self, relation: Relation):
        self.relations[relation.uid] = relation
