# pyright: standard

from dataclasses import fields
from functools import cache
import libcst
import yaml

TAG = "!python/libcst/node:{typename}"
cfields = cache(fields)


class CSTNodeYAMLHelper:
    def __init__(self) -> None:
        self.node_count_dumped = 0
        self.node_count_loaded = 0

    def on_libcst_node(
        self, dumper: yaml.SafeDumper, node: libcst.CSTNode
    ) -> yaml.Node:
        typename = type(node).__name__
        d = {
            f.name: v
            for f in cfields(type(node))
            if (v := getattr(node, f.name)) != f.default
        }
        n = dumper.represent_mapping(TAG.format(typename=typename), d)
        self.node_count_dumped += 1
        return n

    def on_maybe_default(
        self, dumper: yaml.SafeDumper, node: libcst.MaybeSentinel
    ) -> yaml.Node:
        return dumper.represent_scalar("!python/libcst/MaybeSentinel", node.name)

    def load_libcst_node(
        self, loader: yaml.SafeLoader, suffix: str, node
    ) -> libcst.CSTNode:
        typename = suffix
        cls = getattr(libcst, typename)
        d = loader.construct_mapping(node, deep=True)
        self.node_count_loaded += 1
        return cls(**d)  # type: ignore

    def load_libcst_maybe_default(
        self, loader: yaml.SafeLoader, node
    ) -> libcst.MaybeSentinel:
        p = loader.construct_scalar(node)
        return libcst.MaybeSentinel[p]

    def get_dumper_type(self) -> type[yaml.SafeDumper]:
        CSTDumper = type("CSTDumper", (yaml.SafeDumper,), {})
        CSTDumper.add_multi_representer(libcst.CSTNode, self.on_libcst_node)
        CSTDumper.add_representer(libcst.MaybeSentinel, self.on_maybe_default)
        return CSTDumper

    def get_loader_type(self) -> type[yaml.SafeLoader]:
        CSTLoader = type("CSTLoader", (yaml.SafeLoader,), {})
        CSTLoader.add_multi_constructor("!python/libcst/node:", self.load_libcst_node)
        CSTLoader.add_constructor(
            "!python/libcst/MaybeSentinel", self.load_libcst_maybe_default
        )
        return CSTLoader

    def reset_counts(self) -> None:
        self.node_count_dumped = 0
        self.node_count_loaded = 0


def dump(node: libcst.CSTNode) -> str:
    helper = CSTNodeYAMLHelper()
    return yaml.dump(node, Dumper=helper.get_dumper_type())


def main() -> None:
    import tempfile

    fn = tempfile.__file__

    with open(fn, "r") as f:
        tree = libcst.parse_module(f.read())

    helper = CSTNodeYAMLHelper()
    with tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+") as f:
        yaml.dump(tree, f, indent=4, Dumper=helper.get_dumper_type())
        f.seek(0)
        print("Total nodes dumped:", helper.node_count_dumped)
        print("Total size:", len(f.read()))
        f.seek(0)
        helper.reset_counts()
        t: libcst.Module = yaml.load(f, Loader=helper.get_loader_type())
        print("Total nodes loaded:", helper.node_count_loaded)
    assert tree.deep_equals(t)
    assert tree.code == t.code


if __name__ == "__main__":
    main()
    print(cfields.cache_info())
