from itertools import count


def fast_digits(n: int) -> tuple[int, ...]:
    """Return the digits of a integer as a tuple.

    This function is optimized for speed compared to converting the integer
    to a string and then iterating over the characters.

    Parameters
    ----------
    n : int
        A integer whose digits are to be extracted.
    Returns
    -------
    tuple[int, ...]
        A tuple containing the digits of the integer in order.
    """
    n = abs(n)
    if n == 0:
        return (0,)
    digits: list[int] = []
    while n > 0:
        digits.insert(0, n % 10)
        n //= 10
    return tuple(digits)


def find_prefix_and_cycle_decimals(
    p: int, q: int
) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    """Find the prefix and cycle of the decimal representation of p/q.

    Parameters
    ----------
    p : int
        The numerator.
    q : int
        The denominator.

    Returns
    -------
    tuple[int, tuple[int, ...], tuple[int, ...]]
        A tuple containing three elements:
        - The first element contains the integer part.
        - The second element contains the digits of the non-repeating prefix.
        - The third element contains the digits of the repeating cycle.
    """

    sign = -1 if (p * q) < 0 else 1
    p, q = abs(p), abs(q)
    if q == 0:
        raise ZeroDivisionError("Denominator cannot be zero.")
    integer_part, remainder = divmod(p, q)
    integer_part *= sign
    seen_remainders: dict[int, int] = {}
    decimals: list[int] = []
    index = 0

    while remainder != 0:
        if remainder in seen_remainders:
            cycle_start_index = seen_remainders[remainder]
            prefix = tuple(decimals[:cycle_start_index])
            cycle = tuple(decimals[cycle_start_index:])
            return integer_part, prefix, cycle

        seen_remainders[remainder] = index
        remainder *= 10
        decimal_digit = remainder // q
        decimals.append(decimal_digit)
        remainder %= q
        index += 1

    return integer_part, tuple(decimals), ()


curr = -1
for cand in count(start=1):
    _, _, next_curr = find_prefix_and_cycle_decimals(1, cand)
    # if next_curr == ():
    #     break
    if len(next_curr) > curr:
        print(f"1/{cand}, length: {len(next_curr)}")
        curr = len(next_curr)
