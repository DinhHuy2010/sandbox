# pyright: standard

from pathlib import Path
from typing import Iterable

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Static


class InvalidExtension(ModalScreen[None]):
    # 1. Updated CSS selectors to match class names ('.') instead of IDs ('#')
    # 2. Changed 'MessageBox' to 'InvalidExtension' to match the class name
    CSS = """
    InvalidExtension {
        align: center middle;
        background: rgba(0, 0, 0, 0.5); 
    }

    .dialog-box {
        grid-size: 1;
        grid-rows: 1fr 1fr auto; /* Adjusted to give room for both lines of text + button */
        background: $surface;
        border: thick $accent;
        padding: 1 2;
        width: 50;
        height: 15;
    }

    .message-text {
        text-align: center;
        height: 100%;
        content-align: center middle;
    }

    #ok-button {
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        # Changed id to classes to match your CSS definition
        with Grid(classes="dialog-box"):
            yield Static("Invalid file extension", classes="message-text")
            yield Static("Please select a valid file", classes="message-text")
            yield Button("OK", id="ok-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-button":
            # Preferred way to dismiss a specific modal screen
            self.dismiss()


class GlobFilteredDirectoryTree(DirectoryTree):
    """DirectoryTree that only shows files matching one or more glob patterns."""

    def __init__(
        self,
        path: str | Path,
        glob_pattern: str | Iterable[str],
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            path,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )
        if isinstance(glob_pattern, str):
            self.glob_patterns = (glob_pattern,)
        else:
            self.glob_patterns = tuple(glob_pattern)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for path in paths:
            if path.is_dir() or any(
                path.match(pattern) for pattern in self.glob_patterns
            ):
                yield path


class AskOpenFilenameApp(App[Path]):
    def __init__(
        self,
        path: str | Path = "./",
        glob_pattern: str | Iterable[str] = "*",
    ) -> None:
        super().__init__()
        self.root_path = Path(path)
        if isinstance(glob_pattern, str):
            self.glob_patterns = (glob_pattern,)
        else:
            self.glob_patterns = tuple(glob_pattern)
        self.path: Path | None = None
        self.invalid_extensions = {".pyc", ".pyo", ".pyd", ".so", ".dll"}

    def compose(self) -> ComposeResult:
        pattern_label = ", ".join(self.glob_patterns)
        yield Static(
            f"Select a file matching {pattern_label} to open (Press Ctrl+C to cancel)"
        )
        yield GlobFilteredDirectoryTree(self.root_path, self.glob_patterns)

    @on(GlobFilteredDirectoryTree.FileSelected)
    def on_path(self, event: GlobFilteredDirectoryTree.FileSelected) -> None:
        self.path = event.path
        if self.path.suffix in self.invalid_extensions:
            # Re-set path to None so a bad selection doesn't accidentally get returned on crash/exit
            self.path = None
            self.push_screen(InvalidExtension())
            return

        # Pass the final chosen path directly to exit()
        self.exit(result=event.path)


def ask_path(
    path: str | Path = "./",
    glob_pattern: str | Iterable[str] = "*",
) -> Path:
    app = AskOpenFilenameApp(path, glob_pattern)
    # app.run() returns whatever was passed to self.exit(...)
    chosen_path = app.run()

    if chosen_path is None:
        raise RuntimeError("No file selected")
    return chosen_path


if __name__ == "__main__":
    try:
        fn = ask_path(glob_pattern=["*.py", "*.txt"])
        print(f"Successfully selected: {fn}")
    except RuntimeError as e:
        print(f"Selection cancelled: {e}")
