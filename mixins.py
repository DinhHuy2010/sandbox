import secrets
from typing import Any

def mixin(*bases: type[Any], name: str | None = None) -> type[Any]:
    """
    Create a new class that combines multiple base classes.
    """
    if not bases:
        raise ValueError("At least one base class is required")

    # Deduplicate while preserving order
    unique_bases = tuple(dict.fromkeys(bases))

    class_name = name or f"Mixin_{secrets.token_hex(8)}"

    return type(class_name, unique_bases, {})

print(mixin(list, mixin(list, mixin(object, list))))  # Example usage
