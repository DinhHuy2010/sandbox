from typing import Any

from can_ada import URLSearchParams, parse

from libresolver.protocol import protocol_resolve


def resolve(path: str) -> Any:
    """Resolve a given path using ada_url's parse_url function.

    Args:
        path (str): The path to resolve.

    Returns:
        Any: The resolved object.
    """
    parts = parse(path)
    scheme = parts.protocol.strip(":")
    cmd, *args = parts.pathname.split("/")
    return protocol_resolve(
        scheme, cmd, tuple(args), URLSearchParams(parts.search), parts.hash
    )

def init_core() -> None:
    """Initialize the core module."""
    from libresolver.protocol import load_protocol_from_path
    load_protocol_from_path("libresolver.python")
