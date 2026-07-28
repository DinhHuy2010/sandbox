import ast
from hashlib import md5
import importlib.util
from collections import deque


class ImportGraph:
    def __init__(self, root_filename):
        self.root_filename = root_filename
        self.graph = {}
        self.module_to_filenames = {}
        self.id_to_module_pair = {}
        # Keep track of what we have already scanned to prevent infinite loops
        self.visited_ids = set()

    def _init_graph(self):
        self.module_to_filenames["__main__"] = self.root_filename
        self.graph[self.get_id("__main__", self.root_filename)] = set()

    def _get_id(self, name, filename):
        return md5(f"{name}:{filename}".encode()).hexdigest()

    def resolve_id(self, id):
        return self.id_to_module_pair[id]

    def get_id(self, name, filename):
        id = self._get_id(name, filename)
        self.id_to_module_pair[id] = (name, filename)
        return id

    def add_import(self, importer_id, imported_id):
        if importer_id not in self.graph:
            self.graph[importer_id] = set()
        self.graph[importer_id].add(imported_id)

    def resolve_module_to_filename(self, module_name, current_filename):
        if not module_name:  # Fix for relative imports (e.g., 'from . import x')
            return "<relative import>"

        if module_name in self.module_to_filenames:
            return self.module_to_filenames[module_name]

        try:
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                filename = spec.origin
                if filename is None:
                    filename = "<unknown source>"
            else:
                filename = "<module not found>"
        except Exception:
            filename = "<error resolving>"

        self.module_to_filenames[module_name] = filename
        return filename

    def collect_imports(self, module, filename):
        # Prevent trying to open built-ins, missing files, or C-extensions
        if filename.startswith("<") or filename == "built-in":
            return set()

        discovered_imports = set()
        try:
            with open(filename, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filename)
        except Exception as e:
            # Silently log or ignore unreadable files
            return discovered_imports

        importer_id = self.get_id(module, filename)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get base module name (e.g., 'os.path' -> 'os')
                    base_module = alias.name.split(".")[0]
                    imported_filename = self.resolve_module_to_filename(
                        base_module, filename
                    )
                    imported_id = self.get_id(base_module, imported_filename)
                    self.add_import(importer_id, imported_id)
                    discovered_imports.add(imported_id)

            elif isinstance(node, ast.ImportFrom):
                base_module = node.module
                # Handle relative imports safely
                if base_module:
                    base_module = base_module.split(".")[0]
                else:
                    base_module = "<relative>"

                imported_filename = self.resolve_module_to_filename(
                    base_module, filename
                )
                imported_id = self.get_id(base_module, imported_filename)
                self.add_import(importer_id, imported_id)
                discovered_imports.add(imported_id)

        return discovered_imports

    def run(self):
        self._init_graph()
        root_id = self.get_id("__main__", self.root_filename)

        # Use a queue to dynamically process imports layer by layer
        queue = deque([root_id])

        while queue:
            current_id = queue.popleft()
            if current_id in self.visited_ids:
                continue
            self.visited_ids.add(current_id)

            name, filename = self.resolve_id(current_id)
            # Collect and link
            child_ids = self.collect_imports(name, filename)

            # Queue up newly discovered modules for parsing
            for child_id in child_ids:
                if child_id not in self.visited_ids:
                    queue.append(child_id)

def print_graph(graph, level=0, visited=None):
    if visited is None:
        visited = set()
    def print_node(node_id, level):
        if node_id in visited:
            print("  " * level + f"{graph.resolve_id(node_id)[0]} (already visited)")
            return
        visited.add(node_id)
        name, filename = graph.resolve_id(node_id)
        print("  " * level + f"{name} ({filename})")
        for child_id in graph.graph.get(node_id, []):
            print_node(child_id, level + 1)
    print_node(graph.get_id("__main__", graph.root_filename), level)

# --- Run it on itself ---
if __name__ == "__main__":
    graph = ImportGraph(__file__)
    graph.run()

    print("\n=== Final Import Graph ===")
    print_graph(graph)
