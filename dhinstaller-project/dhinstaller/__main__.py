"""Interactive command-line entry point for dhinstaller."""

from __future__ import annotations

import asyncio
import sys

from packaging.specifiers import SpecifierSet
from packaging.utils import parse_wheel_filename
from simple_repository.components.http import HttpRepository

from dhinstaller import (
    download_package,
    get_console,
    inject_fake_venv,
    install_wheel,
    size_to_str,
)
from dhinstaller.artifact_selector import find_best_artifacts
from dhinstaller.context import InstallerContext, RepositoryContext
from dhinstaller.downloader import Aria2Downloader, create_client

console = get_console()

repository = HttpRepository("https://pypi.org/simple/")

# env = select_enviroment()
env = inject_fake_venv("3.10")
package = console.input("Package name to install: ")
with console.status("Pulling package information from PyPI..."):
    project = asyncio.run(repository.get_project_page(package))
name = project.name
console.print(f"Found project: [blue]{project.name}[/blue]")
if not project.versions:
    console.print("[red]No versions found for this project.[/red]")
    sys.exit(1)
console.print("Available versions:")
for version in project.versions:
    console.print(f"- [yellow]{version}[/yellow]")
constriants = None
while True:
    version = console.input(
        "Select version to install (or press enter to select the latest): "
    )
    if not version:
        break
    if version in project.versions:
        constriants = SpecifierSet(f"=={version}")
        break
    console.print(
        "[red]Invalid version. Please select from the available versions.[/red]"
    )
best_artifact, dist_type = find_best_artifacts(env, project.files, constriants)
if not best_artifact:
    console.print("[red]No compatible artifacts found for this environment.[/red]")
    sys.exit(1)
console.print(
    f"Selected artifact: [yellow]{best_artifact.filename}[/yellow] ({size_to_str(best_artifact.size)}) {dist_type})"
)
if dist_type != "wheel":
    console.print(
        "[red]Selected artifact is not a wheel. Cannot install (for now).[/red]"
    )
    sys.exit(1)
_, version, _, _ = parse_wheel_filename(best_artifact.filename)
context = InstallerContext(
    name=project.name,
    version=version,
    env=env,
    repository=RepositoryContext("https://pypi.org/simple/"),
)
with create_client() as aria2_client:
    downloader = Aria2Downloader(aria2_client)
    f = asyncio.run(download_package(context, best_artifact, downloader))
console.print(f"Downloaded file: [yellow]{best_artifact.filename}[/yellow]")
# console.print("Installing package...")
install_wheel(f, env)
