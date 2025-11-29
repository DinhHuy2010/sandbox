"""A simple Click CLI application that fetches data from an API."""

import click
import requests


@click.command()
@click.option("--name", default="World", help="Name to greet.")
@click.option("--fetch", is_flag=True, help="Fetch a random joke from the internet.")
def main(name: str, fetch: bool) -> None:
    """A simple CLI application using Click and Requests."""
    click.echo(f"Hello, {name}!")

    if fetch:
        try:
            response = requests.get(
                "https://official-joke-api.appspot.com/random_joke",
                timeout=10,
            )
            response.raise_for_status()
            joke = response.json()
            click.echo(f"\nHere's a joke for you:")
            click.echo(f"  {joke['setup']}")
            click.echo(f"  {joke['punchline']}")
        except requests.RequestException as e:
            click.echo(f"Could not fetch joke: {e}", err=True)


if __name__ == "__main__":
    main()
