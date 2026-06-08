"""Download helpers and downloader implementations for package artifacts."""

from __future__ import annotations

import secrets
import subprocess
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from shutil import which
from time import sleep

import aria2p
import httpx
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from dhinstaller import get_console
from dhinstaller.context import InstallerContext

DEFAULT_ARTIFACT_DOWNLOADS = Path("./artifact-downloads").resolve()


def is_port_in_use(port: int) -> bool:
    """Check whether a local TCP port is accepting connections.

    Parameters
    ----------
    port
        TCP port on localhost to test.

    Returns
    -------
    bool
        ``True`` if the port accepts a connection, otherwise ``False``.
    """
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


@contextmanager
def start_aria2_daemon():
    """Start an ``aria2c`` RPC process for the duration of a context.

    Yields
    ------
    tuple[subprocess.Popen, int, str]
        Running process, selected RPC port, and RPC secret token.

    Raises
    ------
    RuntimeError
        If the ``aria2c`` executable cannot be found.
    """
    console = get_console()
    console.print("Starting aria2c daemon...")
    aria2c = which("aria2c")
    if aria2c is None:
        raise RuntimeError(
            "aria2c is not installed. Please install it to use the downloader."
        )
    port = 6800
    while is_port_in_use(port):
        console.print(f"Port {port} is in use. Trying next port...")
        port += 1

    secret = secrets.token_hex(16)
    args = [
        aria2c,
        "--enable-rpc",
        # "--rpc-listen-all=true",
        "--rpc-allow-origin-all=true",
        f"--rpc-listen-port={port}",
        "--dir=/tmp/installer-downloads",
        # "--daemon=true",
    ]
    console.print(f"Running command: [yellow]{' '.join(args)}[/yellow]")
    args.append(f"--rpc-secret={secret}")
    with subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ) as p:
        console.print(f"Started aria2c with PID {p.pid}")
        sleep(1)
        yield p, port, secret


@contextmanager
def create_client():
    """Create an aria2 API client backed by a temporary daemon.

    Yields
    ------
    aria2p.API
        API client connected to the managed ``aria2c`` process.
    """
    console = get_console()
    with start_aria2_daemon() as (p, port, secret):
        client = aria2p.Client(port=port, secret=secret)
        try:
            yield aria2p.API(client)
        finally:
            p.terminate()
            p.wait()
    console.print("Aria2c daemon stopped.")


class BaseDownloader(ABC):
    """Abstract base class for artifact downloader implementations."""

    PROIOITY: int = -1

    @abstractmethod
    def download(self, context: InstallerContext, url: str, filename: str) -> Path:
        """Download a URL to a local artifact file.

        Parameters
        ----------
        context
            Installer context containing environment and package information.
        url
            URL to download.
        filename
            Name to use for the local artifact file.

        Returns
        -------
        pathlib.Path
            Local path of the downloaded file.

        Raises
        ------
        NotImplementedError
            Always raised by the abstract base implementation.
        """
        raise NotImplementedError("Downloader must implement download method")


class HTTPXDownloader(BaseDownloader):
    """Downloader implementation that streams artifacts with HTTPX."""

    PROIOITY = 0

    def __init__(self):
        """Initialize the HTTPX downloader and output directory."""
        self.client = httpx.Client(headers={"User-Agent": "dhinstaller/0.1"})
        self.console = get_console()
        self.download_dir = DEFAULT_ARTIFACT_DOWNLOADS

    def download(self, context: InstallerContext, url: str, filename: str) -> Path:
        """Download a file with an HTTPX streaming request.

        Parameters
        ----------
        context
            Installer context containing environment and package information.
        url
            URL to download.
        filename
            Name to use for the downloaded file.

        Returns
        -------
        pathlib.Path
            Path to the downloaded artifact.
        """
        with self.client.stream("GET", url) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            with self.console.status(f"Downloading {filename}..."):
                with Progress(transient=True, console=self.console) as progress:
                    task = progress.add_task(
                        f"Downloading {filename}...", total=total_size
                    )
                    downloaded = 0
                    output_path = self.download_dir / filename
                    with output_path.open("wb") as f:
                        for chunk in response.iter_bytes():
                            downloaded += f.write(chunk)
                            progress.update(task, completed=downloaded)
        # self.console.print(f"Download complete: [yellow]{filename}[/yellow]")
        return output_path


class Aria2Downloader(BaseDownloader):
    """Downloader implementation that delegates artifact downloads to aria2."""

    PROIOITY = 1

    def __init__(self, client: aria2p.API | None = None):
        """Initialize the aria2 downloader.

        Parameters
        ----------
        client
            Existing aria2 API client used to schedule downloads.
        """
        self.client = client
        self.console = get_console()
        self.download_dir = DEFAULT_ARTIFACT_DOWNLOADS

    def download(self, context: InstallerContext, url: str, filename: str) -> Path:
        """Download a file by scheduling it with aria2.

        Parameters
        ----------
        context
            Installer context containing environment and package information.
        url
            URL to download.
        filename
            Name to use for the downloaded file.

        Returns
        -------
        pathlib.Path
            Path to the downloaded artifact.

        Raises
        ------
        RuntimeError
            If no aria2 API client was provided.
        """
        if self.client is None:
            raise RuntimeError("Aria2Downloader requires an aria2p.API client")
        output_path = self.download_dir / filename
        download_file(self.client, url, self.download_dir, filename, context)
        return output_path


DEFAULT_ARIA2C_OPTIONS = {
    "max-connection-per-server": 16,
    "split": 16,
    "auto-file-renaming": False,
    "continue": True,
    "user-agent": "dhinstaller/0.1",
}


def download_file(
    client: aria2p.API,
    url: str,
    output_directory: Path,
    filename: str,
    context: InstallerContext,
):
    """Download a file through aria2 while rendering progress.

    Parameters
    ----------
    client
        aria2 API client used to create and poll the download.
    url
        URL to download.
    output_directory
        Directory where aria2 should place the downloaded file.
    filename
        Display name for the progress task.
    context
        Installer context containing environment and package information.
    """
    console = get_console()
    # console.print(f"Adding download for [yellow]{url}[/yellow] to aria2c...")
    download = client.add_uris(
        [url], {"dir": str(output_directory), **DEFAULT_ARIA2C_OPTIONS}
    )
    # console.print(f"Download added with GID: [yellow]{download.gid}[/yellow]")
    with Progress(
        TextColumn(
            "[progress.description]{task.description}",
        ),
        BarColumn(),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Downloading {context.name}=={context.version}...",
            total=download.total_length,
        )
        while True:
            # console.print(
            #     f"Download status: [yellow]{download.status}[/yellow] {download.completed_length}/{download.total_length} bytes"
            # )
            download.update()
            if download.is_complete:
                # console.print(
                #     f"Download completed: To [green]{output_directory}[/green]"
                # )
                break
            elif download.error_code and download.error_message:
                console.print(
                    f"[red]Error downloading {url}: {download.error_message} ({download.error_code})[/red]"
                )
                break
            else:
                progress.update(
                    task,
                    completed=download.completed_length,
                    total=download.total_length,
                )
            sleep(0.5)
