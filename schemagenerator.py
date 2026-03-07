# pyright: strict

import json
import runpy
from sys import stderr
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Callable, TypeGuard

import faker

DRAFT_URL = "https://json-schema.org/draft/2020-12/schema"

PRIMITIVE_TYPES = ["string", "integer", "number", "boolean", "null"]

type JSONSchemaObject = dict[str, Any]
type JSONSchemaSimpleConstraint = bool
type JSONSchema = JSONSchemaObject | JSONSchemaSimpleConstraint
type TypedSchemaGenerator = Callable[[int, Options], JSONSchema]
type EnumGenerator = Callable[[JSONSchemaObject], list[Any]]
type Generator = tuple[TypedSchemaGenerator, EnumGenerator | None]


f = faker.Faker()
schemas: dict[str, Generator] = {}


class NILType:
    def __bool__(self) -> bool:
        return False


NIL = NILType()


class Options(SimpleNamespace):
    if TYPE_CHECKING:
        depth: int
        clear_defs: bool
        remove_unused_refs: bool

    def __getattr__(self, name: str) -> Any | NILType:
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return NIL


def is_nil(value: Any) -> TypeGuard[NILType]:
    return isinstance(value, NILType)


DEFAULT = Options(
    depth=3,
    clear_defs=True,
    remove_unused_refs=False,
)


def get_options(conf: str, /, **overrides: Any) -> Options:
    opts = runpy.run_path(conf).get("schema_generator_options", {})
    return Options(**(vars(DEFAULT) | opts | overrides))


def register_schema(
    type: str,
    generator: TypedSchemaGenerator,
    enum_generator: EnumGenerator | None = None,
):
    schemas[type] = (generator, enum_generator)


def random_property_name():
    return f.random_element(["-", "_", ""]).join(f.words(nb=f.random_int(1, 3)))


def random_title():
    return "".join(f.words(nb=f.random_int(1, 3))).capitalize()


def random_description():
    return f.sentence()


def random_minmax(min_value: int, max_value: int) -> tuple[int, int]:
    if min_value >= max_value:
        raise ValueError("min_value must be less than max_value")
    min_val = f.random_int(min_value, max_value - 1)
    max_val = f.random_int(min_val + 1, max_value)
    return min_val, max_val


def random_string_schema(depth: int, options: Options) -> JSONSchemaObject:
    schema: JSONSchemaObject = {"type": "string"}
    minl, maxl = random_minmax(1, 15)
    if f.boolean(chance_of_getting_true=50):
        schema["minLength"] = minl
    if f.boolean(chance_of_getting_true=30):
        schema["maxLength"] = maxl

    return schema


def random_string_enum_generator(schema: JSONSchemaObject) -> list[str]:
    min_length = schema.get("minLength", 1)
    max_length = schema.get("maxLength", min_length + 10)
    return [
        f.word()
        for _ in range(f.random_int(1, 5))
        if min_length <= len(f.word()) <= max_length
    ]


register_schema("string", random_string_schema, random_string_enum_generator)


def random_numberish_schema(type: str) -> Generator:
    def gen(depth: int, options: Options) -> JSONSchemaObject:
        schema: JSONSchemaObject = {"type": type}
        nmin, nmax = random_minmax(0, 100)
        if f.boolean(chance_of_getting_true=60):
            schema["minimum"] = nmin
        if f.boolean(chance_of_getting_true=60):
            schema["maximum"] = nmax
        if f.boolean(chance_of_getting_true=30):
            schema["multipleOf"] = f.random_int(1, 10)
        return schema

    def enum_gen(schema: JSONSchemaObject) -> list[int | float]:
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", minimum + 100)
        multiple_of = schema.get("multipleOf", 1)
        return [
            (f.pyint if type == "integer" else f.pyfloat)(
                min_value=minimum, max_value=maximum
            )
            * multiple_of
            for _ in range(f.random_int(1, 5))
        ]

    return gen, enum_gen


register_schema("integer", *random_numberish_schema("integer"))
register_schema("number", *random_numberish_schema("number"))


def random_boolean_schema(depth: int, options: Options) -> JSONSchemaObject:
    return {"type": "boolean"}


def random_null_schema(depth: int, options: Options) -> JSONSchemaObject:
    return {"type": "null"}


register_schema("boolean", random_boolean_schema)
register_schema("null", random_null_schema)


def random_array_schema(depth: int, options: Options) -> JSONSchemaObject:
    min, max = random_minmax(0, 10)
    schema: JSONSchemaObject = {"type": "array"}
    schema["items"] = random_schema(depth - 1)
    if f.boolean(chance_of_getting_true=50):
        schema["minItems"] = min
    if f.boolean(chance_of_getting_true=50):
        schema["maxItems"] = max
    if f.boolean(chance_of_getting_true=30):
        schema["uniqueItems"] = f.random_element([True, False])
    return schema


register_schema("array", random_array_schema)


def random_object_schema(depth: int, options: Options) -> JSONSchemaObject:
    schema: JSONSchemaObject = {"type": "object"}
    properties: dict[str, JSONSchemaObject | JSONSchemaSimpleConstraint] = {}
    required: list[str] = []
    pmin, pmax = random_minmax(0, 10)

    if f.boolean(chance_of_getting_true=50):
        schema["minProperties"] = pmin
    if f.boolean(chance_of_getting_true=50):
        schema["maxProperties"] = pmax

    for _ in range(f.random_int(pmin, pmax)):
        name = random_property_name()
        properties[name] = random_schema(depth - 1)
        if f.boolean(chance_of_getting_true=50):
            required.append(name)

    schema["properties"] = properties

    if required:
        schema["required"] = required

    if f.boolean(chance_of_getting_true=30):
        schema["additionalProperties"] = random_schema(depth - 1)

    return schema


register_schema("object", random_object_schema)


def multi_schema(depth: int, options: Options) -> JSONSchemaObject:
    schema: JSONSchemaObject = {}
    keywords = ["allOf", "anyOf", "oneOf"]
    for element in f.random_elements(keywords, length=f.random_int(1, 3), unique=True):
        schema[element] = [random_schema(depth - 1) for _ in range(f.random_int(2, 5))]
    return schema


register_schema("multi", multi_schema)

refs: dict[str, JSONSchema] = {}
used_refs: set[str] = set()


def unused_refs() -> dict[str, JSONSchema]:
    return {k: v for k, v in refs.items() if k not in used_refs}


def has_refs() -> bool:
    return len(refs) > 0


def generate_ref_path() -> str:
    return f.uuid4()


def push_ref(schema: JSONSchema) -> str | None:
    if f.boolean(chance_of_getting_true=30):
        ref_path = generate_ref_path()
        print("Pushing ref:", ref_path, file=stderr)
        refs[ref_path] = schema
        return ref_path
    return None


def schema_ref(depth: int, options: Options) -> JSONSchemaObject:
    if not has_refs():
        raise ValueError("No refs available")
    k = f.random_element(refs.keys())
    used_refs.add(k)
    return {"$ref": f"#/definitions/{k}"}


register_schema("ref", schema_ref)


def simple_schema(depth: int, options: Options) -> JSONSchemaSimpleConstraint:
    return f.boolean(chance_of_getting_true=50)


register_schema("simple", simple_schema)


def get_schema_options(depth: int) -> list[str]:
    options = [*PRIMITIVE_TYPES, "simple"]
    if has_refs():
        options.append("ref")
    if depth >= 0:
        options.extend(["array", "object", "multi"])
    return options


def generate_from_gen(generator: Generator, depth: int, options: Options) -> JSONSchema:
    gen, enum_gen = generator
    schema = gen(depth, options)
    if (
        enum_gen
        and f.boolean(chance_of_getting_true=30)
        and not isinstance(schema, bool)
    ):
        enum_values = enum_gen(schema)
        schema["enum"] = enum_values
    return schema


def random_schema(depth: int = 3, options: Options = DEFAULT) -> JSONSchema:
    # print(depth, file=stderr)
    choices = get_schema_options(depth)
    choice = f.random_element(choices)
    schema = generate_from_gen(schemas[choice], depth, options)
    push_ref(schema)
    if isinstance(schema, dict):
        return {**base_meta(), **schema}
    return schema


def base_meta() -> JSONSchemaObject:
    return {
        "title": random_title().capitalize(),
        "description": random_description(),
    }


def generate_schema(*, options: Options = DEFAULT) -> JSONSchemaObject:
    d = {
        "$schema": DRAFT_URL,
        "$id": f"https://example.com/{random_title()}.schema.json",
        **random_object_schema(
            depth=options.depth if not is_nil(options.depth) else 3, options=options
        ),
    }
    if has_refs():
        if options.remove_unused_refs:
            d["definitions"] = unused_refs()
        else:
            d["definitions"] = refs.copy()
    if options.clear_defs:
        refs.clear()
    return d


if __name__ == "__main__":
    schema = generate_schema(options=Options(depth=4))
    print(json.dumps(schema, indent=2))
