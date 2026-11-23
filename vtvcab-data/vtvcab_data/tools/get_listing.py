from datetime import date
from pathlib import Path
from sys import stderr, stdout

import anyio
import msgspec
import typer

from vtvcab_data.lib import pull_listing


def main(request_date: str, output: Path | None = None, quiet: bool = False) -> None:
    try:
        request_date = date.fromisoformat(request_date)
    except ValueError:
        typer.echo("Invalid date format. Please use YYYY-MM-DD.", file=stderr)
        raise typer.Exit(code=1)
    if not quiet:
        typer.echo(f"--> Requesting listing for date: {request_date}", file=stderr)
    data = anyio.run(pull_listing, request_date)
    if output is not None:
        with open(output, "wb") as f:
            f.write(msgspec.json.encode(data.data))
    else:
        stdout.buffer.write(msgspec.json.encode(data.data))


if __name__ == "__main__":
    typer.run(main)
