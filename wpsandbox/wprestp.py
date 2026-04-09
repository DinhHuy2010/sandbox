import orjson
import re
from dataclasses import dataclass


@dataclass
class PathParam:
    name: str
    pattern: str


_NAMED_GROUP_RE = re.compile(
    r"\(\?P<(?P<name>[A-Za-z_][A-Za-z0-9_]*)>(?P<pattern>[^)]+)\)"
)

_OPTIONAL_SEGMENT_RE = re.compile(
    r"/\?\(\?P<(?P<name>[A-Za-z_][A-Za-z0-9_]*)>(?P<pattern>[^)]+)\)\?"
)


def wp_regex_path_to_openapi_paths(route: str) -> list[tuple[str, list[PathParam]]]:
    def normalize_pattern(pattern: str) -> str:
        cleaned = pattern.strip()
        cleaned = cleaned.replace(r"[\d]", r"\d")
        cleaned = cleaned.replace(r"[\w]", r"\w")
        return f"^{cleaned}$"

    optional_matches = list(_OPTIONAL_SEGMENT_RE.finditer(route))
    variants = [route]

    for match in optional_matches:
        start, end = match.span()
        name = match.group("name")
        pattern = match.group("pattern")

        next_variants: list[str] = []
        for variant in variants:
            optional_text = match.group(0)

            # branch 1: segment omitted
            next_variants.append(variant.replace(optional_text, "", 1))

            # branch 2: segment included
            replacement = f"/(?P<{name}>{pattern})"
            next_variants.append(variant.replace(optional_text, replacement, 1))

        variants = next_variants

    results: list[tuple[str, list[PathParam]]] = []
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()

    for variant in variants:
        params: list[PathParam] = []

        def replace_named_group(match: re.Match[str]) -> str:
            name = match.group("name")
            pattern = match.group("pattern")
            params.append(PathParam(name=name, pattern=normalize_pattern(pattern)))
            return f"{{{name}}}"

        openapi_path = _NAMED_GROUP_RE.sub(replace_named_group, variant)
        openapi_path = re.sub(r"//+", "/", openapi_path)
        openapi_path = openapi_path.rstrip("/") or "/"

        key = (openapi_path, tuple((p.name, p.pattern) for p in params))
        if key not in seen:
            seen.add(key)
            results.append((openapi_path, params))

    return results

def main() -> None:
    with open("wprestapi-example-2.json", "rb") as f:
        data = orjson.loads(f.read())

    print("Name:", data["name"])
    print("Description:", data["description"])
    print("URL:", data["url"])
    print("Home URL:", data["home"])
    print("WordPress API namespaces:")
    ns = data["namespaces"]
    for n in ns:
        print("  -", n)
    print("Is WordPress REST API supported?:", end=" ")
    if "wp/v2" in ns:
        print("Yes")
    else:
        print("No")
    print("Routes:")
    routes = data["routes"]
    for r in routes:
        print("  -", r)
        print(wp_regex_path_to_openapi_paths(r))
# print("REST API routes:")
# for r in routes:
#     if r.startswith("/wp/v2/"):
#         print("  -", r)
