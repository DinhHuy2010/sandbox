# from typing import Any
# import httpx

# def fetch_ia_metadata(id: str) -> dict[str, Any]:
#     """Fetch metadata for a given Internet Archive item ID.

#     Args:
#         id (str): The Internet Archive item ID.
#     Returns:
#         dict[str, Any]: The metadata dictionary for the item.
#     """

#     url = f"https://archive.org/metadata/{id}"
#     response = httpx.get(url)
#     response.raise_for_status()
#     return response.json()

# print(fetch_ia_metadata("stats"))  # Replace "example_id" with a valid IA item ID for testing.

from collections import deque
from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, cast


class NodeType(str, Enum):
    dict = "dict"
    list = "list"
    node = "node"


def build_path(parts: list[str]) -> str:
    return f"/{'/'.join(parts)}"


@dataclass(kw_only=True, repr=False, frozen=True)
class Node:
    obj: Any
    path_parts: list[str]
    is_root: bool
    type: NodeType

    @property
    def path(self) -> str:
        return build_path(self.path_parts)

    @property
    def parent(self) -> str | None:
        if len(self.path_parts) == 0:
            return None
        return build_path(self.path_parts[:-1])

    @property
    def key(self) -> str | None:
        if len(self.path_parts) == 0:
            return None
        return self.path_parts[-1]

    def __repr__(self):
        return f"Node(path={self.path!r}, type={self.type.value!r})"


# (object, is_root, type, path)
type StackItem = tuple[Any, bool, NodeType, list[str]]


def walk_json_non_recursive(obj: Any):
    def inspect_type(o: Any) -> NodeType:
        if isinstance(o, dict):
            return NodeType.dict
        elif isinstance(o, list):
            return NodeType.list
        else:
            return NodeType.node

    stacks: deque[StackItem] = deque([(obj, True, inspect_type(obj), [])])

    while stacks:
        current, is_root, node_type, current_path = stacks.pop()
        yield Node(
            obj=current,
            is_root=is_root,
            type=node_type,
            path_parts=current_path,
        )
        if isinstance(current, dict):
            for k, v in reversed(cast(dict[Any, Any], current).items()):
                stacks.append(
                    (
                        v,
                        False,
                        inspect_type(v),
                        current_path + [str(k)],
                    )
                )
        elif isinstance(current, list):
            current = cast(list[Any], current)
            for i in range(len(current) - 1, -1, -1):
                v = current[i]
                stacks.append(
                    (
                        v,
                        False,
                        inspect_type(v),
                        current_path + [str(i)],
                    )
                )


with open("ia_meta.json", "r") as f:
    d = json.load(f)

d.pop("files", None)

for node in walk_json_non_recursive(d):
    print(node.path, node.obj)
w