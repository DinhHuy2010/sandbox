# UV Codespace Template

A GitHub Codespace template with UV-managed Python project. This template provides a ready-to-use Python development environment with the UV package manager.

## What is GitHub Codespaces?

GitHub Codespaces is a cloud-based development environment. Think of it as a computer in the cloud that you can access from your browser. When you open a Codespace, you get:

- A full development environment with VS Code in your browser
- Pre-installed tools and dependencies
- Your code ready to run

**Why use it?** You don't need to install anything on your computer. Just click a button and start coding!

## What is a Dev Container?

A dev container (development container) is a Docker container configured specifically for development. The `.devcontainer/` folder in this repository contains:

- **`Dockerfile`**: Instructions to build the container image (like a recipe for your development environment)
- **`devcontainer.json`**: Configuration for VS Code and the container (extensions, settings, startup commands)

When you open this repository in a Codespace, GitHub reads these files and creates your development environment automatically.

## What is UV?

[UV](https://docs.astral.sh/uv/) is a fast Python package manager written in Rust. It replaces tools like `pip`, `pip-tools`, and `virtualenv` with a single, faster tool.

**Key features:**
- 10-100x faster than pip
- Creates and manages virtual environments automatically
- Resolves dependencies reliably

## Getting Started

### Option 1: Use GitHub Codespaces (Recommended for Beginners)

1. Click the green **"Code"** button at the top of this repository
2. Select the **"Codespaces"** tab
3. Click **"Create codespace on main"**
4. Wait for the environment to build (this may take a few minutes the first time)
5. You're ready to code!

### Option 2: Local Development

If you prefer to work locally, you'll need:

1. [Python 3.12+](https://www.python.org/downloads/)
2. [UV package manager](https://docs.astral.sh/uv/getting-started/installation/)

Then run:

```bash
# Clone the repository
git clone <your-repository-url>
cd uv-codespace-template

# Install dependencies
uv sync

# Run the application
uv run hello
```

## Running the Application

This template includes a simple CLI application (`hello.py`) that demonstrates using Click and Requests:

```bash
# Basic greeting
uv run python hello.py

# Greet someone specific
uv run python hello.py --name "Alice"

# Fetch a random joke from the internet
uv run python hello.py --fetch

# Combine options
uv run python hello.py --name "Bob" --fetch
```

## Project Structure

```
uv-codespace-template/
├── .devcontainer/
│   ├── devcontainer.json  # VS Code and container configuration
│   └── Dockerfile         # Container build instructions
├── hello.py               # Sample Click CLI application
├── pyproject.toml         # Project configuration and dependencies
└── README.md              # This file
```

## Common UV Commands

| Command | Description |
|---------|-------------|
| `uv sync` | Install all dependencies from pyproject.toml |
| `uv add <package>` | Add a new dependency |
| `uv remove <package>` | Remove a dependency |
| `uv run <command>` | Run a command in the virtual environment |

## Customizing This Template

1. **Change the project name**: Edit `pyproject.toml` and update the `name` field
2. **Add dependencies**: Run `uv add <package-name>` to add new packages
3. **Modify the CLI**: Edit `hello.py` to create your own application
4. **Add VS Code extensions**: Edit `.devcontainer/devcontainer.json` to include more extensions

## Troubleshooting

**"uv: command not found"**
- In Codespaces: Try reopening the terminal or rebuilding the container
- Locally: Make sure UV is installed and in your PATH

**Dependencies not installing**
- Run `uv sync` manually in the terminal

**Python version mismatch**
- This template requires Python 3.12+. Check your version with `python --version`

## License

This template is open source and available for anyone to use.
