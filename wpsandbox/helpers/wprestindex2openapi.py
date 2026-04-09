from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openapi_pydantic import (
    Contact,
    Info,
    MediaType,
    OpenAPI,
    Operation,
    Parameter,
    ParameterLocation,
    PathItem,
    Reference,
    Response,
    Schema,
    Server,
    Tag,
)


@dataclass(frozen=True)
class PathParam:
    name: str
    pattern: str


HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
SCHEMALESS_METHODS = {"HEAD", "OPTIONS"}

WP_TYPE_TO_OPENAPI_TYPE: dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
}


def _strip_query_regex(route: str) -> str:
    i = 0
    while i < len(route):
        if route[i] == "(":
            # try detect (\?.*)
            if route.startswith(r"(\?", i):
                # remove this group completely
                depth = 1
                j = i + 1
                escaped = False

                while j < len(route):
                    ch = route[j]

                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            return route[:i]  # CUT EVERYTHING AFTER
                    j += 1
        i += 1
    return route


def _normalize_pattern(pattern: str) -> str:
    cleaned = pattern.strip()
    cleaned = cleaned.replace(r"[\d]", r"\d")
    cleaned = cleaned.replace(r"[\w]", r"\w")
    return f"^{cleaned}$"


def _parse_named_group(text: str, start: int) -> tuple[str, str, int] | None:
    if text.startswith("(?P<", start):
        name_start = start + len("(?P<")
    elif text.startswith("(?<", start):
        name_start = start + len("(?<")
    else:
        return None

    name_end = text.find(">", name_start)
    if name_end == -1:
        return None

    name = text[name_start:name_end]
    i = name_end + 1
    depth = 1
    pattern_chars: list[str] = []
    escaped = False

    while i < len(text):
        ch = text[i]

        if escaped:
            pattern_chars.append(ch)
            escaped = False
        elif ch == "\\":
            pattern_chars.append(ch)
            escaped = True
        elif ch == "(":
            pattern_chars.append(ch)
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return name, "".join(pattern_chars), i + 1
            pattern_chars.append(ch)
        else:
            pattern_chars.append(ch)

        i += 1

    return None


def _expand_optional_segments(route: str) -> list[str]:
    results = [route]
    changed = True

    while changed:
        changed = False
        next_results: list[str] = []

        for variant in results:
            i = 0
            expanded = False

            while i < len(variant) - 2:
                if variant[i : i + 2] == "/?":
                    parsed = _parse_named_group(variant, i + 2)
                    if parsed is not None:
                        name, pattern, end = parsed
                        if end < len(variant) and variant[end] == "?":
                            omitted = variant[:i] + variant[end + 1 :]
                            included = (
                                variant[:i]
                                + f"/(?P<{name}>{pattern})"
                                + variant[end + 1 :]
                            )
                            next_results.append(omitted)
                            next_results.append(included)
                            changed = True
                            expanded = True
                            break
                i += 1

            if not expanded:
                next_results.append(variant)

        results = next_results

    seen: set[str] = set()
    deduped: list[str] = []
    for item in results:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def wp_regex_path_to_openapi_paths(route: str) -> list[tuple[str, list[PathParam]]]:
    route = _strip_query_regex(route)
    results: list[tuple[str, list[PathParam]]] = []
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()

    for variant in _expand_optional_segments(route):
        params: list[PathParam] = []
        out: list[str] = []
        i = 0

        while i < len(variant):
            parsed = _parse_named_group(variant, i)
            if parsed is None:
                out.append(variant[i])
                i += 1
                continue

            name, pattern, end = parsed
            params.append(PathParam(name=name, pattern=_normalize_pattern(pattern)))
            out.append(f"{{{name}}}")
            i = end

        openapi_path = "".join(out)
        while "//" in openapi_path:
            openapi_path = openapi_path.replace("//", "/")
        openapi_path = openapi_path.rstrip("/") or "/"

        key = (openapi_path, tuple((p.name, p.pattern) for p in params))
        if key not in seen:
            seen.add(key)
            results.append((openapi_path, params))

    return results


def _is_enum_mapping(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value
        and all(isinstance(k, (str, int)) for k in value.keys())
    )


def _infer_scalar_type_from_value(value: Any) -> str | None:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    return None


def wp_arg_to_schema(arg_name: str, arg_spec: Any) -> Schema:
    if not isinstance(arg_spec, dict):
        return Schema(type="string", title=arg_name)

    arg_type = arg_spec.get("type")
    if isinstance(arg_type, list):
        non_null_types = [t for t in arg_type if t != "null"]
        arg_type = non_null_types[0] if len(non_null_types) == 1 else None

    enum_value = arg_spec.get("enum")
    if _is_enum_mapping(enum_value):
        enum_value = list(enum_value.values())

    schema_kwargs: dict[str, Any] = {"title": arg_name}

    if isinstance(arg_type, str) and arg_type in WP_TYPE_TO_OPENAPI_TYPE:
        schema_kwargs["type"] = WP_TYPE_TO_OPENAPI_TYPE[arg_type]
    else:
        inferred = _infer_scalar_type_from_value(arg_spec.get("default"))
        if inferred is not None:
            schema_kwargs["type"] = inferred
        elif "items" in arg_spec:
            schema_kwargs["type"] = "array"
        elif (
            "properties" in arg_spec or arg_spec.get("additionalProperties") is not None
        ):
            schema_kwargs["type"] = "object"
        else:
            schema_kwargs["type"] = "string"

    description = arg_spec.get("description")
    if isinstance(description, str) and description.strip():
        schema_kwargs["description"] = description.strip()

    if "default" in arg_spec:
        schema_kwargs["default"] = arg_spec["default"]

    if isinstance(enum_value, list) and enum_value:
        schema_kwargs["enum"] = enum_value

    if isinstance(arg_spec.get("format"), str):
        schema_kwargs["format"] = arg_spec["format"]

    for src, dst in (
        ("minimum", "minimum"),
        ("maximum", "maximum"),
        ("exclusiveMinimum", "exclusiveMinimum"),
        ("exclusiveMaximum", "exclusiveMaximum"),
        ("minLength", "minLength"),
        ("maxLength", "maxLength"),
        ("minItems", "minItems"),
        ("maxItems", "maxItems"),
        ("multipleOf", "multipleOf"),
        ("pattern", "pattern"),
    ):
        if src in arg_spec:
            schema_kwargs[dst] = arg_spec[src]

    if "items" in arg_spec:
        items_spec = arg_spec["items"]
        if isinstance(items_spec, dict):
            schema_kwargs["items"] = wp_arg_to_schema(f"{arg_name}Item", items_spec)

    if "properties" in arg_spec and isinstance(arg_spec["properties"], dict):
        schema_kwargs["properties"] = {
            key: wp_arg_to_schema(key, value)
            for key, value in arg_spec["properties"].items()
        }

    if "additionalProperties" in arg_spec:
        additional = arg_spec["additionalProperties"]
        if isinstance(additional, bool):
            schema_kwargs["additionalProperties"] = additional
        elif isinstance(additional, dict):
            schema_kwargs["additionalProperties"] = wp_arg_to_schema(
                f"{arg_name}AdditionalProperty",
                additional,
            )

    required_props = arg_spec.get("requiredProperties")
    if isinstance(required_props, list) and required_props:
        schema_kwargs["required"] = [str(x) for x in required_props]

    return Schema(**schema_kwargs)


def build_parameter(
    name: str,
    schema: Schema,
    location: ParameterLocation,
    required: bool,
    description: str | None = None,
) -> Parameter:
    kwargs: dict[str, Any] = {
        "name": name,
        "in": location,
        "required": required,
        "schema": schema,
    }
    if description:
        kwargs["description"] = description
    return Parameter(**kwargs)


def merge_parameters(
    path_params: list[PathParam],
    args: dict[str, Any],
) -> list[Parameter | Reference]:
    parameters: list[Parameter | Reference] = []
    path_param_names = {p.name for p in path_params}

    for path_param in path_params:
        existing = args.get(path_param.name, {})
        description = None
        if isinstance(existing, dict):
            raw_description = existing.get("description")
            if isinstance(raw_description, str) and raw_description.strip():
                description = raw_description.strip()

        schema = wp_arg_to_schema(path_param.name, existing)
        schema.pattern = path_param.pattern
        if schema.type is None:
            schema.type = "string"

        parameters.append(
            build_parameter(
                name=path_param.name,
                schema=schema,
                location=ParameterLocation.PATH,
                required=True,
                description=description,
            )
        )

    for arg_name, arg_spec in args.items():
        if arg_name in path_param_names:
            continue

        description = None
        required = False
        if isinstance(arg_spec, dict):
            raw_description = arg_spec.get("description")
            if isinstance(raw_description, str) and raw_description.strip():
                description = raw_description.strip()
            required = bool(arg_spec.get("required", False))

        schema = wp_arg_to_schema(arg_name, arg_spec)
        parameters.append(
            build_parameter(
                name=arg_name,
                schema=schema,
                location=ParameterLocation.QUERY,
                required=required,
                description=description,
            )
        )

    return parameters


def build_operation_id(method: str, namespace: str, path: str) -> str:
    normalized_namespace = namespace.strip("/") or "root"
    normalized_path = path.strip("/") or "root"
    parts = [method.lower(), normalized_namespace, normalized_path]
    raw = "_".join(parts)
    raw = raw.replace("/", "_")
    raw = raw.replace("{", "")
    raw = raw.replace("}", "")
    raw = re.sub(r"[^A-Za-z0-9_]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw or f"{method.lower()}_operation"


SCHEMA_ANY = Schema(type=["string", "number", "boolean", "array", "object", "null"])


def build_responses(method: str) -> dict[str, Response | Reference]:
    if method in SCHEMALESS_METHODS:
        return {"204": Response(description="No content")}
    return {
        "200": Response(
            description="Successful response",
            content={"application/json": MediaType(schema=SCHEMA_ANY)},
        ),
        "default": Response(description="Unexpected error"),
    }


def operation_from_endpoint(
    *,
    method: str,
    namespace: str,
    openapi_path: str,
    path_params: list[PathParam],
    endpoint_spec: dict[str, Any],
) -> Operation:
    args = endpoint_spec.get("args", {})
    if not isinstance(args, dict):
        args = {}

    parameters = merge_parameters(path_params, args)
    tags = [namespace] if namespace else None

    summary = f"{method} {openapi_path}"
    description = None
    if namespace:
        description = f"Call API route {openapi_path}, generated from WordPress REST namespace `{namespace}`."

    return Operation(
        operationId=build_operation_id(method, namespace, openapi_path),
        summary=summary,
        description=description,
        tags=tags,
        parameters=parameters or None,
        responses=build_responses(method),
        deprecated=False,
    )


def normalize_route_methods(route_spec: dict[str, Any]) -> list[str]:
    methods = route_spec.get("methods", [])
    if isinstance(methods, list):
        out = [
            m.upper()
            for m in methods
            if isinstance(m, str) and m.upper() in HTTP_METHODS
        ]
        if out:
            return out

    endpoint_methods: list[str] = []
    endpoints = route_spec.get("endpoints", [])
    if isinstance(endpoints, list):
        for endpoint in endpoints:
            if not isinstance(endpoint, dict):
                continue
            for method in endpoint.get("methods", []):
                if isinstance(method, str) and method.upper() in HTTP_METHODS:
                    endpoint_methods.append(method.upper())

    deduped: list[str] = []
    seen: set[str] = set()
    for method in endpoint_methods:
        if method not in seen:
            seen.add(method)
            deduped.append(method)
    return deduped


def build_path_item_for_variant(
    *,
    route: str,
    route_spec: dict[str, Any],
    openapi_path: str,
    path_params: list[PathParam],
) -> PathItem:
    namespace = route_spec.get("namespace", "")
    endpoints = route_spec.get("endpoints", [])
    if not isinstance(endpoints, list):
        endpoints = []

    operations: dict[str, Operation] = {}

    for endpoint_spec in endpoints:
        if not isinstance(endpoint_spec, dict):
            continue
        endpoint_methods = endpoint_spec.get("methods", [])
        if not isinstance(endpoint_methods, list):
            continue

        for method in endpoint_methods:
            if not isinstance(method, str):
                continue
            method_upper = method.upper()
            if method_upper not in HTTP_METHODS:
                continue

            operations[method_upper.lower()] = operation_from_endpoint(
                method=method_upper,
                namespace=namespace,
                openapi_path=openapi_path,
                path_params=path_params,
                endpoint_spec=endpoint_spec,
            )

    if not operations:
        for method in normalize_route_methods(route_spec):
            operations[method.lower()] = Operation(
                operationId=build_operation_id(method, namespace, openapi_path),
                summary=f"{method} {openapi_path}",
                tags=[namespace] if namespace else None,
                responses=build_responses(method),
                deprecated=False,
            )

    kwargs: dict[str, Any] = {}
    for field_name in ("get", "put", "post", "delete", "options", "head", "patch"):
        if field_name in operations:
            kwargs[field_name] = operations[field_name]

    if "summary" not in kwargs:
        kwargs["summary"] = f"Generated from WordPress route `{route}`"

    return PathItem(**kwargs)


def merge_path_items(existing: PathItem, new: PathItem) -> PathItem:
    data = existing.model_dump(by_alias=True, exclude_none=True)
    new_data = new.model_dump(by_alias=True, exclude_none=True)

    for method in ("get", "put", "post", "delete", "options", "head", "patch", "trace"):
        if method in new_data:
            data[method] = new_data[method]

    if "summary" not in data and "summary" in new_data:
        data["summary"] = new_data["summary"]
    if "description" not in data and "description" in new_data:
        data["description"] = new_data["description"]

    return PathItem.model_validate(data)


def wp_index_to_openapi(index: dict[str, Any], api_url: str) -> OpenAPI:
    site_name = str(index.get("name") or "WordPress REST API")
    site_description = index.get("description")
    site_url = str(index.get("url") or "/")

    routes = index.get("routes", {})
    if not isinstance(routes, dict):
        raise TypeError("index['routes'] must be a dict")

    paths: dict[str, PathItem] = {}

    tag_names = sorted(
        {
            spec.get("namespace")
            for spec in routes.values()
            if isinstance(spec, dict)
            and isinstance(spec.get("namespace"), str)
            and spec.get("namespace")
        }
    )
    tags = [Tag(name=tag_name) for tag_name in tag_names] or None

    for raw_route, route_spec in routes.items():
        if not isinstance(raw_route, str) or not isinstance(route_spec, dict):
            continue

        variants = wp_regex_path_to_openapi_paths(raw_route)
        for openapi_path, path_params in variants:
            path_item = build_path_item_for_variant(
                route=raw_route,
                route_spec=route_spec,
                openapi_path=openapi_path,
                path_params=path_params,
            )
            if openapi_path in paths:
                paths[openapi_path] = merge_path_items(paths[openapi_path], path_item)
            else:
                paths[openapi_path] = path_item

    info = Info(
        title=site_name,
        version="generated-from-wp-index",
        description=site_description if isinstance(site_description, str) else None,
        contact=Contact(url=site_url) if site_url else None,
    )

    return OpenAPI(
        openapi="3.1.1",
        info=info,
        servers=[Server(url=api_url)],
        tags=tags,
        paths=paths,
    )


def load_wp_index(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_openapi_json(document: OpenAPI, path: str | Path) -> None:
    Path(path).write_text(
        document.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    from wptk import discover_wordpress_api, fetch_index, create_context

    with create_context() as ctx:
        api_url = discover_wordpress_api(ctx, "https://www.bluey.tv/")
        print(f"Discovered API URL: {api_url}")
        wp_index = fetch_index(ctx, api_url)
        openapi_doc = wp_index_to_openapi(wp_index.index, api_url)
        dump_openapi_json(openapi_doc, "openapi.json")
        print("OpenAPI document generated and saved to openapi.json")
    # print(openapi_doc.model_dump_json(by_alias=True, exclude_none=True, indent=2))
