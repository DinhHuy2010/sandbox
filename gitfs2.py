import pathlib

import pygit2

repos = {
    "sandbox.git": ".",
    "nixpkgs.git": "/home/huyonnixos/nixpkgs.git",
}


def resolve(name: str):
    repo = pygit2.Repository(repos[name])
    return name, repo


name, repo = resolve("nixpkgs.git")
tree = repo.head.peel(pygit2.Tree)


def build_tree(tree: pygit2.Tree):
    stacks = [(tree, pathlib.PurePosixPath(f"/tree/{tree.id}"))]
    while stacks:
        current_tree, path = stacks.pop()
        for entry in current_tree:
            if entry.type == pygit2.enums.ObjectType.TREE:
                stacks.append((repo[entry.id], path / entry.name))
                yield (f"{path}/{entry.name}/", f"/tree/{entry.id}")
            elif entry.type == pygit2.enums.ObjectType.BLOB:
                yield (f"{path}{entry.name}", f"/blob/{entry.id}")


for path, url in build_tree(tree):
    print(f"{name}{path} -> {name}{url}")
