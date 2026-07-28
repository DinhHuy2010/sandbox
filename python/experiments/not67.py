import typing


def is_67(x: typing.Any) -> typing.TypeGuard[typing.Literal[67]]:
    """
    Check if x is exactly 67.

    Parameters:
    -----------
    x : typing.Any
        The object to check.

    Returns:
    --------
    bool
        True if x is 67, False otherwise.

    Usage:
    -------
    >>> is_67(67)
    True
    >>> is_67(42)
    False
    >>> is_67("67")
    Trueu
    >>> is_67(None)
    False
    """
    return int(x) == 67


print(is_67(67))  # True
