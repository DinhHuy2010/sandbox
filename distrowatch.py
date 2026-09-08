from types import SimpleNamespace
from typing import Any


def to_simplenamespace(data: Any) -> SimpleNamespace:
    """
    Convert a dictionary to a SimpleNamespace object.

    Args:
        data (dict): The dictionary to convert.

    Returns:
        SimpleNamespace: The converted SimpleNamespace object.
    """

    if isinstance(data, dict):
        return SimpleNamespace(**{k: to_simplenamespace(v) for k, v in data.items()})
    elif isinstance(data, list) and not isinstance(data, str):
        return [to_simplenamespace(item) for item in data]
    elif isinstance(data, (str, int, float, bool, type(None))):
        return data
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")


def from_simplenamespace(ns: SimpleNamespace) -> Any:
    """
    Convert a SimpleNamespace object back to a dictionary.

    Args:
        ns (SimpleNamespace): The SimpleNamespace object to convert.

    Returns:
        dict: The converted dictionary.
    """

    if isinstance(ns, SimpleNamespace):
        return {k: from_simplenamespace(v) for k, v in vars(ns).items()}
    elif isinstance(ns, list):
        return [from_simplenamespace(item) for item in ns]
    elif isinstance(ns, (str, int, float, bool, type(None))):
        return ns
    else:
        raise TypeError(f"Unsupported data type: {type(ns)}")


# ns = to_simplenamespace(
#     {
#         "name": "Example",
#         "version": 1.0,
#         "features": {"feature1": True, "feature2": False},
#     }
# )


class Node:
    def __init__(self, name: str, value: Any = None):
        self.name = name
        self.value = value


class Graph(Node):
    def __init__(self, name: str, value: Any = None):
        if value is None:
            value = []
        super().__init__(name, value)

    def add_child(self, child: Node):
        self.value.append(child)

    def __repr__(self):
        return f"Graph(name={self.name!r}, value={self.value!r})"


def print_graph(graph: Graph, indent: int = 0):
    """
    Print the graph structure in a readable format.

    Args:
        graph (Graph): The graph to print.
        indent (int): The current indentation level (used for recursion).
    """
    print(" " * indent + f"Graph: {graph.name}")
    for child in graph.value:
        if isinstance(child, Graph):
            print_graph(child, indent + 4)
        else:
            print(" " * (indent + 4) + f"Node: {child.name}, Value: {child.value}")


root = Graph(name="root")
root.add_child(Node(name="child1", value="value1"))
root.add_child(Node(name="child2", value="value2"))
root.add_child(
    Graph(name="subgraph", value=[Node(name="subchild1", value="subvalue1")])
)
root.add_child(Node(name="child3", value="value3"))
root.add_child(
    Graph(name="subgraph2", value=[Node(name="subchild2", value="subvalue2")])
)
root.add_child(Node(name="child4", value="value4"))
print_graph(root)
