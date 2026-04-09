import importlib
import importlib.metadata
import importlib.resources
from pathlib import Path
import sysconfig
from more_itertools import unique_everseen
from packaging.requirements import Requirement

from markdownmaker.document import Document
from markdownmaker.markdownmaker import (
    Bold,
    Italic,
    Link,
    Image,
    Header,
    HeaderSubLevel,
    List,
    CodeBlock,
    Quote,
    HorizontalRule,
)

SITE_PACKAGES = Path(sysconfig.get_path("purelib"))


def get_all_source_files_package(package: str):
    try:
        r = Path(importlib.resources.files(package))
    except ModuleNotFoundError:
        yield from []
        return
    for f in r.rglob("*.py"):
        parts = f.parts[len(SITE_PACKAGES.parts) :]
        module_name_parts: list[str] = []
        for part in parts:
            if part == "__init__.py":
                continue
            if part.endswith(".py"):
                module_name_parts.append(part[:-3])
            else:
                module_name_parts.append(part)
        module_name = ".".join(module_name_parts)
        yield module_name, "/".join(parts), f.read_text()


def get_all_deps(package: str):
    def gen():
        try:
            dist = importlib.metadata.distribution(package)
        except importlib.metadata.PackageNotFoundError:
            yield from []
            return
        for r in dist.requires or []:
            req = Requirement(r)
            if req.marker is None or req.marker.evaluate():
                yield req
                yield from get_all_deps(req.name)

    return unique_everseen(gen())


package = "pydantic"

doc = Document()
doc.add(Header(f"Source code of {package}"))
with HeaderSubLevel(doc):
    doc.add(Header(f"Package: {package}"))
    with HeaderSubLevel(doc):
        for module_name, path, content in get_all_source_files_package(package):
            doc.add(Header(f"Module: {module_name}"))
            doc.add(CodeBlock(content, language="python"))
    # for dep in get_all_deps(package):
    #     dep = dep.name
    #     doc.add(Header(f"Dependency: {dep}"))
    #     with HeaderSubLevel(doc):
    #         for module_name, path, content in get_all_source_files_package(dep):
    #             doc.add(Header(f"Module: {module_name}"))
    #             doc.add(CodeBlock(content, language="python"))

with open("output.md", "w") as f:
    f.write(doc.write())

# doc.add(Header("Markdown Maker"))
# with HeaderSubLevel(doc):
#     doc.add(Header("A Python library for creating Markdown documents"))
# doc.add(Bold("This is bold text"))
# doc.add(Italic("This is italic text"))
# doc.add(Link("Google", "https://www.google.com"))
# doc.add(HorizontalRule())
# doc.add("normal text")
