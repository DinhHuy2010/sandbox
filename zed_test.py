"""Small Fibonacci utility."""


def fibonacci(n: int) -> int:
    """Return the nth Fibonacci number for a non-negative integer index."""
    if n < 0:
        raise ValueError("n must be non-negative")

    previous, current = 0, 1
    for _ in range(n):
        previous, current = current, previous + current
    return previous
