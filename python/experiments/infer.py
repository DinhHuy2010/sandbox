from io import StringIO
import json
from typing import Any
from pydantic import JsonValue
import yaml

memo: set[int] = set()


def infer_structure_from_any(json_value: JsonValue) -> dict[str, Any]:
    key = id(json_value)
    if key in memo:
        return {"type": "any"}
    memo.add(key)
    if isinstance(json_value, dict):
        schema = {
            "type": "dict",
            "schema": {k: infer_structure_from_any(v) for k, v in json_value.items()},
            "length": len(json_value),
        }
    elif isinstance(json_value, list):
        schema = {
            "type": "list",
            "items": [infer_structure_from_any(j) for j in json_value],
            "length": len(json_value),
        }
    elif isinstance(json_value, str):
        schema = {"type": "str"}
    elif isinstance(json_value, bool):
        schema = {"type": "bool"}
    elif isinstance(json_value, int):
        schema = {"type": "int"}
    elif isinstance(json_value, float):
        schema = {"type": "float"}
    elif json_value is None:
        schema = {"type": "None"}
    else:
        raise ValueError(f"Unsupported JSON value type: {type(json_value)}")
    memo.remove(key)
    return schema


def build_schema_final(type, kwargs) -> dict[str, Any]:
    return {"type": type, **kwargs}


def build_schema_dict(dict_structure: dict[str, Any]) -> dict[str, Any]:
    return build_schema_final(
        "dict",
        {
            "props": {
                k: infer_schema_from_structure(v)
                for k, v in dict_structure["schema"].items()
            },
            "required_keys": list(dict_structure["schema"].keys()),
        },
    )


def build_union_schema(types: list[dict[str, Any]]) -> dict[str, Any]:
    unique_schemas = []
    for t in types:
        if t not in unique_schemas:
            unique_schemas.append(t)
    if len(unique_schemas) == 1:
        return unique_schemas[0]
    else:
        return build_schema_final("union", {"schemas": unique_schemas})


def build_schema_list(list_structure: dict[str, Any]) -> dict[str, Any]:
    items = list_structure["items"]
    if not items:
        return build_schema_final("list", {"items": build_schema_final("any", {})})
    item_schemas = [infer_schema_from_structure(item) for item in items]
    unique_item_schemas = []
    for schema in item_schemas:
        if schema not in unique_item_schemas:
            unique_item_schemas.append(schema)
    if len(unique_item_schemas) == 1:
        return build_schema_final("list", {"items": unique_item_schemas[0]})
    else:
        return build_schema_final(
            "list", {"items": build_union_schema(unique_item_schemas)}
        )

def intern_ref(refs: dict[int, Any], schema: dict[str, Any]) -> dict[str, Any]:
    schema_id = id(schema)
    if schema_id in refs:
        return {"type": "ref", "ref": schema_id}
    else:
        refs[schema_id] = schema
        return {"type": "ref", "ref": schema_id}

def infer_schema_from_structure(structure: dict[str, Any]) -> Any:
    refs = {}
    match structure["type"]:
        case "dict":
            schema = intern_ref(refs, build_schema_dict(structure))
        case "list":
            schema = intern_ref(refs, build_schema_list(structure))
        case "str":
            schema = build_schema_final("str", {})
        case "int":
            schema = build_schema_final("int", {})
        case "float":
            schema = build_schema_final("float", {})
        case "bool":
            schema = build_schema_final("bool", {})
        case "None":
            schema = build_schema_final("None", {})
        case "any":
            schema = build_schema_final("any", {})
        case _:
            raise ValueError(f"Unsupported structure type: {structure['type']}")
    return refs, schema


def merge_schema(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    if a == b:
        return a

    ta = a["type"]
    tb = b["type"]

    if ta == "any":
        return b
    if tb == "any":
        return a

    if ta == "union":
        return build_union_schema(a["schemas"] + [b])
    if tb == "union":
        return build_union_schema([a] + b["schemas"])

    if ta != tb:
        return build_union_schema([a, b])

    if ta == "dict":
        a_props = a["props"]
        b_props = b["props"]
        keys = set(a_props) | set(b_props)

        merged_props = {}
        for key in keys:
            if key in a_props and key in b_props:
                merged_props[key] = merge_schema(a_props[key], b_props[key])
            elif key in a_props:
                merged_props[key] = a_props[key]
            else:
                merged_props[key] = b_props[key]

        a_required = set(a.get("required_keys", a_props.keys()))
        b_required = set(b.get("required_keys", b_props.keys()))

        return {
            "type": "dict",
            "props": merged_props,
            "required_keys": list(a_required & b_required),
        }

    if ta == "list":
        return {"type": "list", "items": merge_schema(a["items"], b["items"])}

    return a


def generate_repr(s):
    match s["type"]:
        case "dict":
            props = ", ".join(f"{k}={generate_repr(v)}" for k, v in s["props"].items())
            return f"dict({props})"
        case "list":
            return f"list({generate_repr(s['items'])})"
        case "str":
            return "str()"
        case "int":
            return "int()"
        case "float":
            return "float()"
        case "bool":
            return "bool()"
        case "None":
            return "none()"
        case "any":
            return "any()"
        case "union":
            return (
                f"union({' | '.join(generate_repr(schema) for schema in s['schemas'])})"
            )
        case _:
            raise ValueError(f"Unsupported schema type: {s['type']}")


def dump_yaml(schema):
    f = StringIO()
    yaml.safe_dump(schema, f, sort_keys=False)
    return f.getvalue()


class SchemaLearner:
    def __init__(self):
        self.schema = {"type": "any"}
        self.refs = {}

    def learn_from_example(self, example: JsonValue):
        structure = infer_structure_from_any(example)
        refs, new_schema = infer_schema_from_structure(structure)
        self.refs.update(refs)
        self.schema = merge_schema(self.schema, new_schema)

    def finalize_schema(self):
        return {"refs": self.refs, **self.schema}


with open("pyrightconfig.schema.json", "r") as f:
    example = json.load(f)
schema_learner = SchemaLearner()
schema_learner.learn_from_example(example)
print(dump_yaml(schema_learner.finalize_schema()))
# example = {
#     "name": "Alice",
#     "age": 30,
#     "is_student": False,
#     "courses": ["Math", "Science"],
#     "address": {"street": "123 Main St", "city": "Anytown"},
# }
# schema_learner = SchemaLearner()
# schema_learner.learn_from_example(example)
# schema_learner.learn_from_example(
#     {
#         "name": "Bob",
#         "age": 25,
#         "is_student": True,
#         "courses": ["History"],
#         "address": {"street": "456 Elm St", "city": "Othertown"},
#     }
# )
# schema_learner.learn_from_example(
#     {
#         "name": "Charlie",
#         "age": 35,
#         "is_student": False,
#         "courses": ["Math", "Literature"],
#         "address": {
#             "street": None,
#             "city": "Sometown",
#             "extra": "This field is only in this example",
#         },
#         "example_field": "This field is only in this example",
#     }
# )
# schema_learner.learn_from_example(
#     {
#         "name": "Charlie",
#         "age": 35,
#         "is_student": False,
#         "courses": ["Math", "Literature"],
#         "address": {"street": None, "city": "Sometown", "extra": None},
#         "example_field": "This field is only in this example",
#     }
# )
# schema_learner.learn_from_example(schema_learner.schema)
# print(dump_yaml(schema_learner.schema))
