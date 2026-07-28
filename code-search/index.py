import ast
from pathlib import Path
from shutil import rmtree

import pathspec
import scandir_rs
import tantivy
import tqdm

TARGET = Path("..").resolve()
INDEX = Path.cwd() / ".cs-index"

schema_builder = tantivy.SchemaBuilder()
schema_builder.add_text_field("filepath", stored=True)
schema_builder.add_text_field("name", stored=True)
schema_builder.add_text_field("type", stored=True)
schema_builder.add_integer_field("line", stored=True)
schema_builder.add_integer_field("col", stored=True)
schema_builder.add_text_field("code", stored=True)
schema = schema_builder.build()

if INDEX.exists():
    print("Removing existing index")
    rmtree(INDEX)
print("Creating new index")
INDEX.mkdir()
index = tantivy.Index(schema, path=str(INDEX))
consumer = index.writer()


def index_file(path: str):
    def add_to_index(name, type_, line, col, code):
        doc = tantivy.Document()
        doc.add_text("filepath", str(path))
        doc.add_text("name", name)
        doc.add_text("type", type_)
        doc.add_integer("line", line)
        doc.add_integer("col", col)
        doc.add_text("code", code)
        consumer.add_document(doc)

    with open(path, "r") as f:
        code = f.read()
        tree = ast.parse(code, filename=path)

    with tqdm.tqdm(total=0, unit="symbol", desc="Indexing...", leave=False) as symbols:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                name = node.name
                line = node.lineno
                col = node.col_offset
                code_snippet = ast.get_source_segment(code, node)
                add_to_index(name, "function", line, col, code_snippet)
                symbols.update(1)
            elif isinstance(node, ast.ClassDef):
                name = node.name
                line = node.lineno
                col = node.col_offset
                code_snippet = ast.get_source_segment(code, node)
                add_to_index(name, "class", line, col, code_snippet)
                symbols.update(1)
        return symbols.n  # Return the number of indexed symbols


sd = scandir_rs.Scandir(str(TARGET))
with open(TARGET / ".gitignore", "r") as f:
    spec = pathspec.PathSpec.from_lines("gitignore", lines=f.readlines())
with open(TARGET / ".git/info/exclude", "r") as f:
    spec += pathspec.PathSpec.from_lines("gitignore", lines=f.readlines())

for i in sd:
    if (
        spec.match_file(i.path)
        or i.path.startswith(".git/")
        or i.path == ".git"
        or not i.path.endswith(".py")
    ):
        continue
    target = TARGET / i.path
    syms = index_file(target)
    print(f"Indexed {syms} symbols from {target}")
    consumer.commit()
