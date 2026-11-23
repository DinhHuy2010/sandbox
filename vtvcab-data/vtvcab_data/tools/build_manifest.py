from pathlib import Path

import anyio
import typer

from vtvcab_data.manifest import ManifestBuilder


def main(directory: Path = typer.Argument(..., help="Directory to build manifest for")):
    """Build manifest for a given directory."""

    builder = ManifestBuilder(directory)

    manifest = anyio.run(
        builder.build, backend="asyncio", backend_options={"use_uvloop": True}
    )
    builder.save(manifest)


if __name__ == "__main__":
    typer.run(main)
