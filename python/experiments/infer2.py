from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json

import more_itertools
from tqdm import tqdm


def infer_structure(data):
    if isinstance(data, str):
        return {"type": "str"}
    elif isinstance(data, bool):
        return {"type": "bool"}
    elif isinstance(data, int):
        return {"type": "int"}
    elif isinstance(data, float):
        return {"type": "float"}
    elif isinstance(data, Decimal):
        return {"type": "decimal"}
    elif data is None:
        return {"type": "null"}
    elif isinstance(data, (frozenset, set)):
        s = {"type": "set", "elements": []}
        for item in data:
            s["elements"].append(infer_structure(item))
        return s
    elif isinstance(data, tuple):
        s = {"type": "tuple", "elements": []}
        for item in data:
            s["elements"].append(infer_structure(item))
        return s
    elif isinstance(data, bytes):
        return {"type": "bytes"}
    elif isinstance(data, datetime):
        return {"type": "datetime"}
    elif isinstance(data, time):
        return {"type": "time"}
    elif isinstance(data, date):
        return {"type": "date"}
    elif isinstance(data, timedelta):
        return {"type": "timedelta"}
    elif isinstance(data, (complex,)):
        return {"type": "complex"}
    elif isinstance(data, list):
        s = {"type": "list", "elements": []}
        for item in data:
            s["elements"].append(infer_structure(item))
        return s
    elif isinstance(data, dict):
        s = {"type": "dict", "properties": {}}
        for key, value in data.items():
            s["properties"][key] = infer_structure(value)
        s["required"] = list(data.keys())
        return s
    else:
        raise RuntimeError(f"Unsupported data type: {type(data)}")


def infer_schema(structure):
    if structure["type"] in {
        "str",
        "int",
        "float",
        "bool",
        "decimal",
        "null",
        "bytes",
        "datetime",
        "time",
        "date",
        "timedelta",
        "complex",
    }:
        return structure
    elif structure["type"] in {"list", "set", "tuple"}:
        typ = structure["type"]
        element_schemas = [infer_schema(element) for element in structure["elements"]]
        return {"type": typ, "elements": merge_schemas(element_schemas)}
    elif structure["type"] == "dict":
        properties = {}
        for key, value in structure["properties"].items():
            properties[key] = infer_schema(value)
        return {
            "type": "dict",
            "properties": properties,
            "required": structure["required"],
        }
    else:
        raise RuntimeError(f"Unsupported structure type: {structure['type']}")


def collapse_union(schema):
    if schema["type"] != "union":
        return schema
    unique_schemas = schema["schemas"]
    if len(unique_schemas) == 1:
        return unique_schemas[0]
    schemas = []
    for s in unique_schemas:
        if s["type"] == "union":
            schemas.extend(s["schemas"])
        else:
            schemas.append(s)
    return {"type": "union", "schemas": list(more_itertools.unique_everseen(schemas))}


def merge_schemas(schemas):
    if not schemas:
        return {"type": "any"}
    unique_schemas = list(more_itertools.unique_everseen(schemas))
    if len(unique_schemas) == 1:
        return unique_schemas[0]
    types = set(schema["type"] for schema in unique_schemas)
    if len(types) == 1:
        # merge schemas of the same type
        if any(x in types for x in {"list", "set", "tuple"}):
            element_schemas = [schema["elements"] for schema in unique_schemas]
            final = {"type": list(types)[0], "elements": merge_schemas(element_schemas)}
        elif "dict" in types:
            all_keys = set()
            for schema in unique_schemas:
                all_keys.update(schema["properties"].keys())
            properties = {}
            required = set()
            for key in all_keys:
                key_schemas = []
                for schema in unique_schemas:
                    if key in schema["properties"]:
                        key_schemas.append(schema["properties"][key])
                properties[key] = merge_schemas(key_schemas)
                if all(key in schema["required"] for schema in unique_schemas):
                    required.add(key)
            final = {
                "type": "dict",
                "properties": properties,
                "required": list(required),
            }
        elif "union" in types:
            final = collapse_union({"type": "union", "schemas": unique_schemas})
        else:
            raise RuntimeError(f"Unsupported schema type for merging: {types}")
    else:
        final = collapse_union({"type": "union", "schemas": unique_schemas})
    assert final is not None
    return final


def pretty_schema(schema):
    match schema["type"]:
        case "str" | "int" | "float" | "bool":
            return f"{schema['type']}()"
        case "list":
            return f"list({pretty_schema(schema['elements'])})"
        case "dict":
            props = ", ".join(
                f"{key}: {pretty_schema(value)}"
                for key, value in schema["properties"].items()
            )
            return f"dict({props})"
        case "union":
            return (
                "union(" + ", ".join(pretty_schema(s) for s in schema["schemas"]) + ")"
            )
        case "set":
            return f"set({pretty_schema(schema['elements'])})"
        case "tuple":
            return f"tuple({pretty_schema(schema['elements'])})"
        case "decimal" | "null" | "bytes" | "datetime" | "time" | "date" | "timedelta" | "complex":
            return f"{schema['type']}()"
        case _:
            raise RuntimeError(f"Unsupported schema type: {schema['type']}")


def infer(samples):
    def b(s):
        return infer_schema(infer_structure(s))

    sit = iter(samples)
    first = next(sit)
    schema = b(first)
    for sample in tqdm(sit):
        schema = merge_schemas([schema, b(sample)])
        # print("=== After processing sample: ===")
        # try:
        #     text = pretty_schema(schema)
        # except Exception as e:
        #     print(f"Error in pretty_schema: {e}")
        #     text = str(schema)
        # if len(text) > 100:
        #     text = text[:100] + "..."
        # print(text)

    return schema


def insane_product():
    from faker import Faker

    fake = Faker()

    fake_str = fake.pystr
    fake_int = fake.pyint
    fake_float = fake.pyfloat
    fake_bool = fake.pybool

    def fake_list():
        return fake.pylist(
            nb_elements=fake.pyint(min_value=1, max_value=5),
            variable_nb_elements=True,
            value_types=[str, int, float, bool, list, dict],
        )

    def fake_dict():
        return fake.pydict(
            nb_elements=fake.pyint(min_value=1, max_value=5),
            variable_nb_elements=True,
            value_types=[str, int, float, bool, list, dict],
        )

    functions = [fake_str, fake_int, fake_float, fake_bool, fake_list, fake_dict]
    for _ in range(fake.random_int(min=10, max=2000)):
        yield fake.random_element(functions)()

schema = infer(insane_product())
print(pretty_schema(schema))