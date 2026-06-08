# pyright: standard
"""Core installation helpers for dhinstaller."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import installer
from installer.destinations import SchemeDictionaryDestination, WheelDestination
from installer.sources import WheelFile
from rich.console import Console, Group
from rich.padding import Padding
from simple_repository.model import File

from dhinstaller.context import InstallerContext
from dhinstaller.environments import (
    Environment,
)
from dhinstaller.environments.discovery import (
    discover_environments as find_python_environments,
)
from dhinstaller.environments.discovery import (
    environment_from_interpreter,
)

if TYPE_CHECKING:
    from dhinstaller.downloader import BaseDownloader

console = Console()


def get_console() -> Console:
    """Return the shared Rich console used by dhinstaller.

    Returns
    -------
    Console
        Global console instance used for user-facing output.
    """
    return console


def size_to_str(size: int) -> str:
    """Format a byte count as a human-readable size.

    Parameters
    ----------
    size
        Size in bytes.

    Returns
    -------
    str
        Size formatted with a binary unit suffix.
    """
    units = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
    for unit, factor in units.items():
        if size < factor * 1024:
            return f"{size / factor:.2f} {unit}"
    return f"{size / units['GiB']:.2f} GiB"


def inject_fake_venv(version: str) -> Environment:
    """Create a temporary virtual environment for a Python version.

    Parameters
    ----------
    version
        Python version or interpreter selector accepted by ``uv venv -p``.

    Returns
    -------
    Environment
        Parsed environment information for the created virtual environment.

    Raises
    ------
    subprocess.CalledProcessError
        If ``uv venv`` fails to create the environment.
    """
    with tempfile.TemporaryDirectory(delete=False) as tmpdir:
        console.print(
            f"Creating temporary virtual environment at [yellow]{tmpdir}[/yellow]"
        )
        p = subprocess.run(
            ["uv", "venv", "-p", version, tmpdir],
            check=True,
            env={**os.environ, "UV_NO_PROJECT": "1"},
        )
        p.check_returncode()
        return environment_from_interpreter(Path(tmpdir) / "bin" / "python")


def select_enviroment():
    """Prompt the user to select a discovered Python environment.

    Returns
    -------
    Environment
        Environment chosen by the user.
    """
    envs = list(find_python_environments())
    group = Group()
    group.renderables.append("[bold]Python environments[/bold]")
    for i, env in enumerate(envs, start=1):
        group.renderables.append(
            Padding(
                f"{i}. [blue]{env.name}[/blue] ([yellow]{env.executable}[/yellow])",
                (0, 0, 0, 2),
            )
        )
    console.print(group)
    while True:
        try:
            choice = int(console.input("Select environment to install package into: "))
            if 1 <= choice <= len(group.renderables) - 1:
                break
        except ValueError:
            console.print("[red]Invalid choice. Please enter a number.[/red]")
            continue
    selected_env = envs[choice - 1]
    console.print(f"Selected environment: [blue]{selected_env.name}[/blue]")
    return selected_env


async def download_package(
    context: InstallerContext,
    file: File,
    downloader: BaseDownloader,
) -> Path:
    """Download an artifact from a project with the provided downloader.

    Parameters
    ----------
    context
        Installer context containing environment and package information.
    file
        Package artifact metadata to download.
    downloader
        Downloader implementation used to retrieve the artifact.

    Returns
    -------
    pathlib.Path
        Local path of the downloaded artifact.
    """
    console.print(
        f"Downloading [yellow]{file.filename}[/yellow] from [blue]{context.name}[/blue]..."
    )
    return downloader.download(context, file.url, file.filename)


class DestWrapper(WheelDestination):
    """A wrapper around WheelDestination that adds console output of installation process."""

    def __init__(self, real_dest: WheelDestination):
        """Initialize the destination wrapper.

        Parameters
        ----------
        real_dest
            Destination that performs the actual wheel installation writes.
        """
        super().__init__()
        self.real_dest = real_dest

    def write_file(self, scheme, path, stream, is_executable):
        """Write an installed wheel file through the wrapped destination.

        Parameters
        ----------
        scheme
            Installation scheme that owns the file.
        path
            Relative destination path for the file.
        stream
            Binary stream containing file contents.
        is_executable
            Whether the file should be marked executable.

        Returns
        -------
        object
            Return value from the wrapped destination.
        """
        console.print(f"Writing file: [yellow]{path}[/yellow]...")
        return self.real_dest.write_file(scheme, path, stream, is_executable)

    def write_script(self, name, module, attr, section):
        """Write an entry-point script through the wrapped destination.

        Parameters
        ----------
        name
            Script name to create.
        module
            Python module containing the callable entry point.
        attr
            Attribute name of the callable entry point.
        section
            Entry-point section that defined the script.

        Returns
        -------
        object
            Return value from the wrapped destination.
        """
        console.print(
            f"Writing {section!r} script: \
[yellow]{name}[/yellow] -> [blue]{module}.{attr}[/blue]..."
        )
        return self.real_dest.write_script(name, module, attr, section)

    def finalize_installation(self, scheme, record_file_path, records):
        """Finalize wheel installation through the wrapped destination.

        Parameters
        ----------
        scheme
            Installation scheme used for finalization.
        record_file_path
            Path to the generated RECORD file.
        records
            Installation records to persist.

        Returns
        -------
        object
            Return value from the wrapped destination.
        """
        console.print(
            f"Finalizing installation for scheme: [yellow]{scheme}[/yellow]..."
        )
        return self.real_dest.finalize_installation(scheme, record_file_path, records)


def install_wheel(wheel_file: Path, env: Environment):
    """Install a wheel file into an environment.

    Parameters
    ----------
    wheel_file
        Path to the wheel file to install.
    env
        Environment that receives the wheel contents.
    """
    with console.status(f"Installing wheel into [blue]{env.name}[/blue]..."):
        if platform.system() == "Windows":
            lanucher_kind = f"win-{platform.machine()}"
        else:
            lanucher_kind = "posix"
        dest = DestWrapper(
            SchemeDictionaryDestination(
                env.scheme_paths,
                str(env.executable),
                lanucher_kind,  # type: ignore
            )
        )

        with WheelFile.open(wheel_file) as source:
            installer.install(
                source,
                dest,
                additional_metadata={
                    "INSTALLER": b"dhinstaller",
                },
            )
    console.print(
        f"Installation complete for [yellow]{wheel_file.name}[/yellow] into [blue]{env.name}[/blue]"
    )
