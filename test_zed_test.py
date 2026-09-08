import pytest

from zed_test import fibonacci


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, 0),
        (1, 1),
        (2, 1),
        (5, 5),
        (10, 55),
    ],
)
def test_fibonacci_returns_expected_value(n: int, expected: int) -> None:
    assert fibonacci(n) == expected


def test_fibonacci_rejects_negative_index() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        fibonacci(-1)
