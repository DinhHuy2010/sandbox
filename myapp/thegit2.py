from pprint import pprint
from typing import Literal, overload
import pygit2
from pygit2.enums import ObjectType


@overload
def build_map(  # type: ignore
    tree: pygit2.Tree, *, include_tree: Literal[False] = False, recursive: bool = False
) -> dict[str, pygit2.Blob]: ...
@overload
def build_map(
    tree: pygit2.Tree, *, include_tree: Literal[True] = True, recursive: bool = False
) -> dict[str, pygit2.Blob | pygit2.Tree]: ...
def build_map(  # type: ignore
    tree: pygit2.Tree, *, include_tree: bool = False, recursive: bool = False
) -> dict[str, pygit2.Blob | pygit2.Tree]:
    result: dict[str, pygit2.Blob | pygit2.Tree] = {}
    for entry in tree:
        if entry.type == ObjectType.BLOB:
            result[entry.name] = entry
        elif entry.type == ObjectType.TREE:
            if include_tree:
                result[entry.name] = entry
            if recursive:
                subtree = entry.peel(pygit2.Tree)
                submap = build_map(
                    subtree, include_tree=include_tree, recursive=recursive
                )
                for subname, subentry in submap.items():
                    result[f"{entry.name}/{subname}"] = subentry
    return result


repo = pygit2.Repository("/tmp/git-git")
repo.branches.with_commit("HEAD")
# for p, b in build_map(repo.head.peel(pygit2.Tree), recursive=True).items():
#     print(p, b.id, len(b.data))
