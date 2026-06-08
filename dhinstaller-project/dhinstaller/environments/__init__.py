# pyright: standard
"""Discovery and representation of Python installation environments."""

from __future__ import annotations

from pathlib import Path

from attrs import define, field
from packaging.version import InvalidVersion, Version

from dhinstaller.environments.utils import parse_venv_info

__sentinel__ = object()


@define
class Environment:
    """Description of an installable Python environment.

    Attributes
    ----------
    name: str
        Display name for the environment.
    executable: pathlib.Path
        Path to the Python executable for the environment.
    version: str
        Python version string reported by the environment.
    scheme_paths: dict[str, str]
        Installation scheme paths for this environment,
        as returned by `sysconfig.get_paths()` on that
        interpreter.
    """

    executable: Path
    version: str
    scheme_paths: dict[str, str]
    _venv_info: dict[str, str] | None = field(
        default=__sentinel__, init=False, repr=False
    )  # type: ignore

    def _get_venv_info(self) -> dict[str, str] | None:
        """Lazily parse and cache virtual environment metadata."""
        if self._venv_info is __sentinel__:
            self._venv_info = parse_venv_info(self.root)
        return self._venv_info

    @property
    def version_tuple(self) -> tuple[int, int, int]:
        """Return the parsed Python version as a tuple.

        Returns
        -------
        tuple[int, int, int]
            Major, minor, and micro version numbers. Invalid versions return
            ``(0, 0, 0)``.
        """
        try:
            version = Version(self.version)
        except InvalidVersion:
            return 0, 0, 0
        return version.major, version.minor, version.micro

    @property
    def site_packages(self) -> Path:
        """Return the site-packages directory for the environment.

        Returns
        -------
        pathlib.Path
            Platform-specific path to the environment's site-packages
            directory.

        Notes
        -----
        This is determined from the environment's installation scheme path
        for "purelib", which is where pip installs packages for pure Python.
        """
        return Path(self.scheme_paths["purelib"])

    @property
    def root(self) -> Path:
        """Return the root directory of the environment.

        Returns
        -------
        pathlib.Path
            Parent directory of the Python executable, which serves as the
            root of the environment.
        """
        return Path(self.scheme_paths["data"])

    @property
    def is_venv(self) -> bool:
        """Return whether this environment is a virtual environment.

        Returns
        -------
        bool
            True if the environment is a virtual environment, False otherwise.
        """
        return self._get_venv_info() is not None

    @property
    def name(self) -> str:
        """Return the display name of the environment.

        Returns
        -------
        str
            The name of the environment, which is either the stem of the
            executable path or a custom name if provided.
        """
        venv_info = self._get_venv_info()
        if venv_info is not None:
            return venv_info.get("prompt", self.root.stem)
        else:
            return self.root.stem

    def __rich__(self):
        """Return a Rich-compatible display representation.

        Returns
        -------
        str
            Markup string showing the environment name and path.
        """
        return f"[blue]{self.name}[/blue] ([yellow]{self.executable}[/yellow])"
