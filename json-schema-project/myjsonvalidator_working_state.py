from typing import Any, NamedTuple
from urllib.parse import unquote, urldefrag, urljoin
import regex as re
from decimal import Decimal, InvalidOperation


class SchemaError(Exception):
    """Raised when a schema is invalid or a referenced schema cannot be resolved."""

    pass


class ValidationError(Exception):
    """Raised when JSON data does not satisfy a schema."""

    pass


class ValidationResult:
    """Annotations collected while validating one schema location."""

    def __init__(self, evaluated_properties=None, evaluated_items=None):
        self.evaluated_properties = set(evaluated_properties or ())
        self.evaluated_items = set(evaluated_items or ())

    def merge(self, other):
        if other is None:
            return self
        self.evaluated_properties.update(other.evaluated_properties)
        self.evaluated_items.update(other.evaluated_items)
        return self


class SchemaRegistry:
    """Stores schema documents and resolves remote documents through opt-in loaders."""

    def __init__(self, documents=None, loaders=None):
        self._documents = {}
        self._loaders = list(loaders or ())
        for uri, document in (documents or {}).items():
            self.register(uri, document)

    def register(self, uri, document):
        """Register a schema document and its nested `$id` resources."""
        self._documents[uri] = document
        collect_schema_resources(document, uri, self)
        return document

    def add_loader(self, loader):
        """Register a callable loader that accepts a URI and returns a schema or None."""
        self._loaders.append(loader)

    def resolve_document(self, uri):
        """Return a registered schema document, or load one through an opt-in loader."""
        if uri in self._documents:
            return self._documents[uri]

        for loader in self._loaders:
            document = loader(uri)
            if document is not None:
                return self.register(uri, document)

        sfail(f"Schema URI could not be resolved: {uri}")

    def get(self, uri):
        return self._documents.get(uri)


def fail(message):
    raise ValidationError(message)


def sfail(message):
    raise SchemaError(message)


def json_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b

    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b

    if type(a) is not type(b):
        return False

    if isinstance(a, list):
        return len(a) == len(b) and all(json_equal(x, y) for x, y in zip(a, b))

    if isinstance(a, dict):
        return a.keys() == b.keys() and all(json_equal(a[k], b[k]) for k in a)

    return a == b


def validate_type(data, schema, schema_context=None):
    if "type" not in schema:
        return

    expected = schema["type"]

    if isinstance(expected, list):
        if any(matches_type(data, t) for t in expected):
            return
        fail(f"Expected one of {expected}, got {type(data).__name__}")
        return

    if not matches_type(data, expected):
        fail(f"Expected {expected}, got {type(data).__name__}")


def match_integer(data):
    return (isinstance(data, int) and not isinstance(data, bool)) or (
        isinstance(data, float) and data.is_integer()
    )


def matches_type(data, expected):
    match expected:
        case "null":
            return data is None
        case "boolean":
            return isinstance(data, bool)
        case "object":
            return isinstance(data, dict)
        case "array":
            return isinstance(data, list)
        case "integer":
            return match_integer(data)
        case "number":
            return isinstance(data, (int, float)) and not isinstance(data, bool)
        case "string":
            return isinstance(data, str)
        case _:
            fail(f"Unknown type: {expected}")


def validate_const(data, schema, schema_context=None):
    if "const" in schema and not json_equal(data, schema["const"]):
        fail(f"Expected const {schema['const']!r}")


def validate_enum(data, schema, schema_context=None):
    if "enum" in schema and not any(json_equal(data, item) for item in schema["enum"]):
        fail(f"Expected one of {schema['enum']!r}")


def validate_number_minimum(data, schema, schema_context=None):
    if not matches_type(data, "number"):
        return

    if "minimum" in schema and data < schema["minimum"]:
        fail(f"{data} is less than minimum {schema['minimum']}")


def validate_number_maximum(data, schema, schema_context=None):
    if not matches_type(data, "number"):
        return

    if "maximum" in schema and data > schema["maximum"]:
        fail(f"{data} is greater than maximum {schema['maximum']}")


def validate_number_exclusive_minimum(data, schema, schema_context=None):
    if not matches_type(data, "number"):
        return

    if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
        fail(
            f"{data} is not greater than exclusiveMinimum {schema['exclusiveMinimum']}"
        )


def validate_number_exclusive_maximum(data, schema, schema_context=None):
    if not matches_type(data, "number"):
        return

    if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
        fail(f"{data} is not less than exclusiveMaximum {schema['exclusiveMaximum']}")


def validate_number_multiple_of(data, schema, schema_context=None):
    if not matches_type(data, "number"):
        return

    if "multipleOf" not in schema:
        return

    try:
        data = Decimal(str(data))
        multiple_of = Decimal(str(schema["multipleOf"]))

        if multiple_of == 0:
            fail("multipleOf cannot be zero")

        if data % multiple_of != 0:
            fail(f"{data} is not multipleOf {multiple_of}")

    except InvalidOperation:
        fail(f"{data} is not multipleOf {schema['multipleOf']}")


def validate_string_min_length(data, schema, schema_context=None):
    if not isinstance(data, str):
        return

    if "minLength" in schema and len(data) < schema["minLength"]:
        fail(f"String too short, minimum length {schema['minLength']}")


def validate_string_max_length(data, schema, schema_context=None):
    if not isinstance(data, str):
        return

    if "maxLength" in schema and len(data) > schema["maxLength"]:
        fail(f"String too long, maximum length {schema['maxLength']}")


def validate_array_min_items(data, schema, schema_context=None):
    if not isinstance(data, list):
        return

    if "minItems" in schema and len(data) < schema["minItems"]:
        fail("Array too short")


def validate_array_max_items(data, schema, schema_context=None):
    if not isinstance(data, list):
        return

    if "maxItems" in schema and len(data) > schema["maxItems"]:
        fail("Array too long")


def validate_array_unique_items(data, schema, schema_context=None):
    if not isinstance(data, list):
        return

    if schema.get("uniqueItems") is True:
        for i in range(len(data)):
            for j in range(i + 1, len(data)):
                if json_equal(data[i], data[j]):
                    fail("Array items are not unique")


def validate_array_items(data, schema, schema_context=None):
    if not isinstance(data, list):
        return ValidationResult()

    result = ValidationResult()
    prefix_start = 0
    if "prefixItems" in schema:
        prefix_items = schema["prefixItems"]
        for i, item_schema in enumerate(prefix_items):
            if i < len(data):
                validate_json(data[i], item_schema, schema_context)
                result.evaluated_items.add(i)
        prefix_start = len(prefix_items)

    if "items" in schema:
        item_schema = schema["items"]
        for offset, item in enumerate(data[prefix_start:], start=prefix_start):
            validate_json(item, item_schema, schema_context)
            result.evaluated_items.add(offset)

    return result


def validate_object_required(data, schema, schema_context=None):
    if not isinstance(data, dict):
        return

    if "required" in schema:
        for key in schema["required"]:
            if key not in data:
                fail(f"Missing required property: {key}")


def validate_object_properties(data, schema, schema_context=None):
    if not isinstance(data, dict):
        return ValidationResult()

    result = ValidationResult()

    if "minProperties" in schema:
        if len(data) < schema["minProperties"]:
            fail(
                f"Object has {len(data)} properties, "
                f"minimum is {schema['minProperties']}"
            )

    if "maxProperties" in schema:
        if len(data) > schema["maxProperties"]:
            fail(
                f"Object has {len(data)} properties, "
                f"maximum is {schema['maxProperties']}"
            )

    properties = schema.get("properties", {})
    pattern_properties = schema.get("patternProperties", {})
    has_additional_properties = "additionalProperties" in schema
    additional = schema.get("additionalProperties", True)

    evaluated = set()

    for name, subschema in properties.items():
        if name in data:
            validate_json(data[name], subschema, schema_context)
            evaluated.add(name)
            result.evaluated_properties.add(name)

    for pattern, subschema in pattern_properties.items():
        regex = re.compile(pattern)

        for name, value in data.items():
            if regex.search(name):
                validate_json(value, subschema, schema_context)
                evaluated.add(name)
                result.evaluated_properties.add(name)

    for name, value in data.items():
        if name in evaluated:
            continue

        if additional is True:
            if has_additional_properties:
                result.evaluated_properties.add(name)
            continue

        if additional is False:
            fail(f"Additional property '{name}' is not allowed")

        validate_json(value, additional, schema_context)
        result.evaluated_properties.add(name)

    return result


def validate_property_names(data, schema, schema_context=None):
    if not isinstance(data, dict):
        return

    if "propertyNames" not in schema:
        return

    name_schema = schema["propertyNames"]

    for name in data:
        validate_json(name, name_schema, schema_context)


def validate_array_contains(data, schema, schema_context=None):
    if not isinstance(data, list):
        return ValidationResult()

    if "contains" not in schema:
        return ValidationResult()

    root_schema = schema_context.root if schema_context else schema

    result = ValidationResult()
    matches = 0

    for index, item in enumerate(data):
        try:
            validate_json(
                item,
                schema["contains"],
                schema_context=schema_context._replace(root=root_schema)
                if schema_context
                else SchemaContext(root=root_schema, registry=SchemaRegistry()),
            )
            matches += 1
            result.evaluated_items.add(index)
        except ValidationError:
            pass

    min_contains = schema.get("minContains", 1)
    max_contains = schema.get("maxContains")

    if matches < min_contains:
        fail(f"contains matched {matches}, expected at least {min_contains}")

    if max_contains is not None and matches > max_contains:
        fail(f"contains matched {matches}, expected at most {max_contains}")

    return result


def _regex_compile(pattern):
    try:
        return re.compile(pattern)
    except re.error as e:
        sfail(f"Invalid regex pattern {pattern!r}: {e}")


def pattern_matches(data, pattern, schema_context=None):

    if not isinstance(data, str):
        return False

    return _regex_compile(pattern).search(data) is not None


def validate_string_pattern(data, schema, schema_context=None):
    if not isinstance(data, str):
        return

    if "pattern" in schema:
        pattern = schema["pattern"]
        if not pattern_matches(data, pattern, schema_context):
            fail(f"String does not match pattern {pattern!r}")


def validate_allof(data, schema, schema_context=None):
    result = ValidationResult()
    if "allOf" in schema:
        for subschema in schema["allOf"]:
            result.merge(validate_json(data, subschema, schema_context))
    return result


def validate_anyof(data, schema, schema_context=None):
    result = ValidationResult()
    if "anyOf" in schema:
        valid_count = 0
        for subschema in schema["anyOf"]:
            try:
                result.merge(validate_json(data, subschema, schema_context))
                valid_count += 1
            except ValidationError:
                continue
        if valid_count == 0:
            fail("Data does not match any of the 'anyOf' schemas")
    return result


def validate_oneof(data, schema, schema_context=None):
    result = ValidationResult()
    if "oneOf" in schema:
        valid_count = 0
        for subschema in schema["oneOf"]:
            try:
                branch_result = validate_json(data, subschema, schema_context)
                valid_count += 1
                result = branch_result
            except ValidationError:
                continue

        if valid_count != 1:
            fail(f"Data matches {valid_count} schemas in 'oneOf', expected exactly one")
    return result


def validate_not(data, schema, schema_context=None):
    if "not" in schema:
        if _is_json_valid(data, schema["not"], schema_context):
            fail("Data matches the 'not' schema, which is not allowed")


def validate_conditional(data, schema, schema_context=None):
    result = ValidationResult()
    if "if" not in schema:
        return result

    try:
        if_result = validate_json(data, schema["if"], schema_context)
        if_matches = True
    except ValidationError:
        if_result = ValidationResult()
        if_matches = False

    if if_matches:
        result.merge(if_result)
        if "then" in schema:
            result.merge(validate_json(data, schema["then"], schema_context))
    else:
        if "else" in schema:
            result.merge(validate_json(data, schema["else"], schema_context))

    return result


def validate_dependent_required(data, schema, schema_context=None):
    if not isinstance(data, dict):
        return

    dependent_required = schema.get("dependentRequired")
    if dependent_required is None:
        return

    for prop, required_props in dependent_required.items():
        if prop not in data:
            continue

        for required_prop in required_props:
            if required_prop not in data:
                fail(f"Property {prop!r} requires property {required_prop!r}")


def validate_dependent_schemas(data, schema, schema_context=None):
    if not isinstance(data, dict):
        return ValidationResult()

    dependent_schemas = schema.get("dependentSchemas")
    if dependent_schemas is None:
        return ValidationResult()

    result = ValidationResult()
    for prop, subschema in dependent_schemas.items():
        if prop in data:
            result.merge(validate_json(data, subschema, schema_context))

    return result


def validate_unevaluated_properties(data, schema, schema_context, current_result):
    if not isinstance(data, dict) or "unevaluatedProperties" not in schema:
        return ValidationResult()

    result = ValidationResult()
    unevaluated_schema = schema["unevaluatedProperties"]

    for name, value in data.items():
        if name in current_result.evaluated_properties:
            continue
        validate_json(value, unevaluated_schema, schema_context)
        result.evaluated_properties.add(name)

    return result


def validate_unevaluated_items(data, schema, schema_context, current_result):
    if not isinstance(data, list) or "unevaluatedItems" not in schema:
        return ValidationResult()

    result = ValidationResult()
    unevaluated_schema = schema["unevaluatedItems"]

    for index, item in enumerate(data):
        if index in current_result.evaluated_items:
            continue
        validate_json(item, unevaluated_schema, schema_context)
        result.evaluated_items.add(index)

    return result


KEYWORDS_TO_VALIDATE = {
    "type": validate_type,
    "const": validate_const,
    "enum": validate_enum,
    "minimum": validate_number_minimum,
    "maximum": validate_number_maximum,
    "exclusiveMinimum": validate_number_exclusive_minimum,
    "exclusiveMaximum": validate_number_exclusive_maximum,
    "multipleOf": validate_number_multiple_of,
    "minLength": validate_string_min_length,
    "maxLength": validate_string_max_length,
    "minItems": validate_array_min_items,
    "maxItems": validate_array_max_items,
    "uniqueItems": validate_array_unique_items,
    ("prefixItems", "items"): validate_array_items,
    "required": validate_object_required,
    (
        "properties",
        "patternProperties",
        "additionalProperties",
        "maxProperties",
        "minProperties",
    ): validate_object_properties,
    "propertyNames": validate_property_names,
    ("contains", "maxContains", "minContains"): validate_array_contains,
    "pattern": validate_string_pattern,
    "allOf": validate_allof,
    "anyOf": validate_anyof,
    "oneOf": validate_oneof,
    "not": validate_not,
    ("if", "then", "else"): validate_conditional,
    "dependentRequired": validate_dependent_required,
    "dependentSchemas": validate_dependent_schemas,
}


def parse_external_ref(ref, base_uri=""):
    full_uri = urljoin(base_uri, ref)
    document_uri, fragment = urldefrag(full_uri)
    return document_uri, fragment


def unescape_json_pointer(pointer):
    return re.sub(r"~1", "/", re.sub(r"~0", "~", pointer))


def resolve_json_pointer(schema, fragment):
    fragment = unquote(fragment)
    if fragment == "":
        return schema
    if not fragment.startswith("/"):
        sfail(f"Invalid JSON Pointer '{fragment}'")

    parts = fragment.lstrip("/").split("/")
    current = schema

    for part in parts:
        part = unescape_json_pointer(part)
        if isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError):
                sfail(f"Invalid array index '{part}' in JSON Pointer '{fragment}'")
        elif isinstance(current, dict):
            if part not in current:
                sfail(f"Key '{part}' not found in JSON Pointer '{fragment}'")
            current = current[part]
        else:
            sfail(
                f"Cannot traverse into non-container type at '{part}' in JSON Pointer '{fragment}'"
            )

    return current


def find_anchor(schema, anchor_name):
    if isinstance(schema, dict):
        if (
            schema.get("$anchor") == anchor_name
            or schema.get("$dynamicAnchor") == anchor_name
        ):
            return schema

        for value in schema.values():
            try:
                return find_anchor(value, anchor_name)
            except SchemaError:
                pass

    elif isinstance(schema, list):
        for item in schema:
            try:
                return find_anchor(item, anchor_name)
            except SchemaError:
                pass

    sfail(f"Anchor not found: {anchor_name}")


def resolve_ref(ref, schema_context):
    document_uri, fragment = parse_external_ref(ref, schema_context.base_uri)

    if document_uri in ("", None):
        target_doc = schema_context.root
        target_base_uri = schema_context.base_uri
    else:
        target_doc = schema_context.registry.resolve_document(document_uri)
        target_base_uri = document_uri

    if fragment.startswith("/"):
        return ResolvedRef(
            resolve_json_pointer(target_doc, fragment), target_doc, target_base_uri
        )
    if fragment:
        return ResolvedRef(
            find_anchor(target_doc, fragment), target_doc, target_base_uri
        )
    return ResolvedRef(target_doc, target_doc, target_base_uri)


def validate_reference(json_data, ref, schema_context):
    resolved_ref = resolve_ref(ref, schema_context)
    return validate_json(
        json_data,
        resolved_ref.schema,
        schema_context._replace(
            root=resolved_ref.root,
            base_uri=resolved_ref.base_uri,
        ),
    )


class SchemaContext(NamedTuple):
    root: Any
    registry: SchemaRegistry
    base_uri: str = ""


class ResolvedRef(NamedTuple):
    schema: Any
    root: Any
    base_uri: str


def collect_schema_resources(schema, base_uri, registry):
    if isinstance(schema, dict):
        current_base_uri = base_uri
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            current_base_uri = urljoin(base_uri, schema_id)
            registry._documents[current_base_uri] = schema

        for value in schema.values():
            collect_schema_resources(value, current_base_uri, registry)
    elif isinstance(schema, list):
        for item in schema:
            collect_schema_resources(item, base_uri, registry)


def validate_json(json_data, schema, schema_context=None, registry=None):
    """Validate JSON data against a Draft 2020-12 schema.

    Returns a ValidationResult on success and raises ValidationError or SchemaError
    on failure. Remote schemas are resolved only through the provided registry.
    """
    if schema is True:
        return ValidationResult()

    if schema is False:
        fail("Boolean schema false rejects everything")

    if not isinstance(schema, dict):
        fail("Schema must be object or boolean")

    if schema_context is None:
        if registry is None:
            registry = SchemaRegistry()
        elif not isinstance(registry, SchemaRegistry):
            registry = SchemaRegistry(documents=registry)
        collect_schema_resources(schema, "", registry)
        schema_context = SchemaContext(root=schema, registry=registry)

    if "$id" in schema:
        if schema_context.registry.get(schema_context.base_uri) is schema:
            new_base_uri = schema_context.base_uri
        else:
            new_base_uri = urljoin(schema_context.base_uri, schema["$id"])
        schema_context = schema_context._replace(
            base_uri=new_base_uri,
        )
        schema_context.registry._documents[new_base_uri] = schema
    if "$ref" in schema:
        result = ValidationResult().merge(
            validate_reference(json_data, schema["$ref"], schema_context)
        )
    else:
        result = ValidationResult()

    if "$dynamicRef" in schema:
        result.merge(
            validate_reference(json_data, schema["$dynamicRef"], schema_context)
        )

    for keyword, validator in KEYWORDS_TO_VALIDATE.items():
        if isinstance(keyword, tuple):
            if any(k in schema for k in keyword):
                result.merge(validator(json_data, schema, schema_context))
        else:
            if keyword in schema:
                result.merge(validator(json_data, schema, schema_context))

    result.merge(
        validate_unevaluated_properties(json_data, schema, schema_context, result)
    )
    result.merge(validate_unevaluated_items(json_data, schema, schema_context, result))

    return result


def _is_json_valid(json_data, schema, schema_context=None, registry=None):
    try:
        validate_json(json_data, schema, schema_context, registry=registry)
        return True
    except ValidationError:
        return False


def is_json_valid(json_data, schema, registry=None):
    """Return True when data validates, otherwise False for validation failures."""
    return _is_json_valid(json_data, schema, registry=registry)
