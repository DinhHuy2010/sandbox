# Python Experiments Workspace

This repository is a collection of Python experiments, utilities, prototypes, and
small standalone projects. The loose scripts that previously lived in the
repository root are organized under `python/` so related code is easier to find.

## Layout

| Directory | Contents |
| --- | --- |
| `python/lib/` | Shared modules imported by other scripts |
| `python/examples/` | Examples and runtime demonstrations |
| `python/tests/` | Tests for the shared modules |
| `python/web/` | HTTP servers, API experiments, and web applications |
| `python/tools/` | Repository, scraping, generation, and command-line utilities |
| `python/games/` | Games and emulators |
| `python/models/` | Data and API model definitions |
| `python/experiments/` | Language, runtime, import, AST, and miscellaneous experiments |

Self-contained projects such as `dhforge/`, `dhinstaller-project/`, `funny/`,
`mycrawler/`, `okwhatever3/`, `pypi/`, `pyinterpeter/`, and `schemagenerator/`
retain their own source trees and project configuration.

## Environment

The root `pyproject.toml` targets Python 3.12 or newer and defines the shared
development dependencies. Install them with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Several nested projects are uv workspace members and may also have their own
`pyproject.toml`, README, or test instructions.

## Running Code

Run commands from the repository root so imports from `python.lib` resolve
consistently:

```bash
uv run python -m python.examples.simplehttp_example
uv run python -m python.tools.generate_qs
uv run python -m python.games.tictactoe
```

Many files are exploratory and may require network access, local services, input
data, or optional packages beyond the shared environment. Read the module before
running it if its purpose is not obvious.

## Tests

The reorganized tests can be run individually:

```bash
uv run pytest python/tests/test_dhruntime2.py
uv run pytest python/tests/test_dhruntime3.py
uv run pytest python/tests/test_rangeresp.py
```

Nested projects keep their own tests in their respective directories.
