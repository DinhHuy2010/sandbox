import anyio
from packaging.specifiers import SpecifierSet
from packaging.utils import parse_sdist_filename, parse_wheel_filename
from packaging.version import Version
from rich.console import Console, Group
from rich.padding import Padding
from simple_repository.components.http import HttpRepository
from simple_repository.model import File

PYTHON_VERSIONS: list[Version] = []
with open("python-versions.txt") as f:
    for line in f:
        PYTHON_VERSIONS.append(Version(line.strip()))


def get_version(filename: str) -> Version | None:
    try:
        return parse_wheel_filename(filename)[1]
    except Exception:
        try:
            return parse_sdist_filename(filename)[1]
        except Exception:
            return None


def filesize(size: float) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} YiB"


repo = HttpRepository("https://pypi.org/simple/")
console = Console()

package = console.input("[bold green]Enter the package name:[/bold green] ")
with console.status("[bold green]Fetching project page...[/bold green]") as status:
    project = anyio.run(repo.get_project_page, package)
console.print(f"[bold green]Package name:[/bold green] {project.name}")
console.print("[bold green]Package directory:[/bold green]")
files: dict[Version, list[File]] = {}
for file in project.files:
    version = get_version(file.filename)
    if version not in files:
        files[version] = []
    files[version].append(file)
total_filesize = 0
for version, file_list in files.items():
    # group = Group()
    ps = [Padding(f"[bold green]{project.name}=={version}[/bold green]", (0, 0, 0, 4))]
    for file in file_list:
        ps.append(
            Padding(
                f"{file.filename} ({filesize(file.size)}, {file.requires_python})",
                (0, 0, 0, 8),
            )
        )
        pyrequires = (
            SpecifierSet(file.requires_python) if file.requires_python else None
        )
        if pyrequires is not None:
            ps.append(
                Padding(
                    f"  - Compatible with Python {
                        ', '.join(str(v) for v in pyrequires.filter(PYTHON_VERSIONS))
                    }",
                    (0, 0, 0, 12),
                )
            )
        total_filesize += file.size
    group = Group(*ps)
    console.print(group)
console.print(f"[bold green]Total filesize:[/bold green] {filesize(total_filesize)}")
