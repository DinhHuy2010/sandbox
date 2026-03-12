from __future__ import annotations

import faker
from dataclasses import dataclass, field, replace
from typing import Any, Generator, Protocol


class SchemaGenerator(Protocol):
    def types(self, context: StateContext) -> list[str] | None:
        return None

    def generate(self, context: StateContext) -> Any: ...

    def generate_enum(self, context: StateContext, schema: Any) -> list[Any] | None:
        return None


class CentralSchemaGenerator:
    def __init__(self) -> None:
        self.register: dict[str, SchemaGenerator] = {}

    def _generate_schema(
        self, generator: SchemaGenerator, context: StateContext
    ) -> Any:
        schema = {}
        types = generator.types(context)
        f = context.get_faker()
        if types is not None:
            if len(types) == 1 and f.boolean():
                types = types[0]
            schema["type"] = types
        schema.update(generator.generate(context))
        enums = generator.generate_enum(context, schema)
        if enums is not None:
            if f.boolean():
                e = f.random_element(enums)
                schema["const"] = e
            else:
                schema["enum"] = enums
        return schema


@dataclass
class StateContext:
    depth: int
    faker_config: dict[str, Any] | None = field(default=None)
    cached_faker: faker.Faker | None = field(default=None, repr=False)
    central_generator: SchemaGenerator | None = field(default=None, repr=False)
    previous_state: StateContext | None = field(default=None, repr=False, init=False)

    def get_faker(self) -> faker.Faker:
        if self.cached_faker is None:
            if self.faker_config is not None:
                self.cached_faker = faker.Faker(**self.faker_config)
            else:
                self.cached_faker = faker.Faker()
        return self.cached_faker

    def next_state(self, reduce_depth_by: int = 1) -> StateContext:
        assert (self.depth - reduce_depth_by) >= 0, "Depth cannot be negative"
        return replace(self, depth=self.depth - reduce_depth_by, previous_state=self)

    def previous_states(self) -> Generator[StateContext]:
        # The current state is excluded
        current = self.previous_state
        while current is not None:
            yield current
            current = current.previous_state
