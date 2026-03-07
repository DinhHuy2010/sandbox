from math import ceil


# ---------------------------
# Helpers
# ---------------------------


def _bit_index(n: int, r: int, c: int) -> int:
    if not (0 <= r < n and 0 <= c < n):
        raise IndexError("out of range")
    return r * n + c


def _get_bit(buf: bytes, bit: int) -> int:
    return (buf[bit >> 3] >> (bit & 7)) & 1


def _set_bit(buf: bytes, bit: int) -> bytes:
    b = bytearray(buf)
    b[bit >> 3] |= 1 << (bit & 7)
    return bytes(b)


def _bytes_to_int(buf: bytes) -> int:
    return int.from_bytes(buf, "little")


def _int_to_bytes(value: int, size: int) -> bytes:
    return value.to_bytes(size, "little")


# ---------------------------
# Board creation
# ---------------------------


def new_board(n: int, players: int) -> bytes:
    if n <= 0 or players <= 0:
        raise ValueError("invalid parameters")
    bits = n * n
    bytes_per_player = ceil(bits / 8)
    return bytes(bytes_per_player * players)


# ---------------------------
# Move
# ---------------------------


def move(
    board: bytes, n: int, players: int, player_index: int, r: int, c: int
) -> bytes:

    bits = n * n
    bytes_per_player = ceil(bits / 8)

    if not (0 <= player_index < players):
        raise ValueError("invalid player")

    bit = _bit_index(n, r, c)

    # Check if cell already occupied
    for p in range(players):
        offset = p * bytes_per_player
        segment = board[offset : offset + bytes_per_player]
        if _get_bit(segment, bit):
            raise ValueError("cell occupied")

    # Set bit for current player
    offset = player_index * bytes_per_player
    segment = board[offset : offset + bytes_per_player]
    updated_segment = _set_bit(segment, bit)

    return board[:offset] + updated_segment + board[offset + bytes_per_player :]


# ---------------------------
# Win mask generation
# ---------------------------


def _win_masks(n: int) -> tuple[int, ...]:
    masks = []

    # Rows
    for r in range(n):
        m = 0
        for c in range(n):
            m |= 1 << (r * n + c)
        masks.append(m)

    # Columns
    for c in range(n):
        m = 0
        for r in range(n):
            m |= 1 << (r * n + c)
        masks.append(m)

    # Main diagonal
    m = 0
    for i in range(n):
        m |= 1 << (i * n + i)
    masks.append(m)

    # Anti-diagonal
    m = 0
    for i in range(n):
        m |= 1 << (i * n + (n - 1 - i))
    masks.append(m)

    return tuple(masks)


# ---------------------------
# Winner check
# ---------------------------


def winner(board: bytes, n: int, players: int) -> int | None:
    bits = n * n
    bytes_per_player = ceil(bits / 8)
    masks = _win_masks(n)

    for p in range(players):
        offset = p * bytes_per_player
        segment = board[offset : offset + bytes_per_player]
        value = _bytes_to_int(segment)

        for m in masks:
            if (value & m) == m:
                return p

    return None


# ---------------------------
# Draw check
# ---------------------------


def is_draw(board: bytes, n: int, players: int) -> bool:
    if winner(board, n, players) is not None:
        return False

    bits = n * n
    bytes_per_player = ceil(bits / 8)

    occupied = 0
    for p in range(players):
        offset = p * bytes_per_player
        segment = board[offset : offset + bytes_per_player]
        occupied |= _bytes_to_int(segment)

    return occupied == (1 << bits) - 1


# ---------------------------
# Render (debug only)
# ---------------------------


def render(board: bytes, n: int, players: int) -> str:
    bits = n * n
    bytes_per_player = ceil(bits / 8)

    symbols = [str(i) for i in range(players)]

    out = []
    for r in range(n):
        row = []
        for c in range(n):
            bit = _bit_index(n, r, c)
            found = "."
            for p in range(players):
                offset = p * bytes_per_player
                segment = board[offset : offset + bytes_per_player]
                if _get_bit(segment, bit):
                    found = symbols[p]
                    break
            row.append(found)
        out.append(" ".join(row))
    return "\n".join(out)


# ---------------------------
# Example
# ---------------------------


def pstats(n: int, players: int, board: bytes) -> list[tuple[int, int]]:
    bits = n * n
    bytes_per_player = ceil(bits / 8)
    players_list = []

    for p in range(players):
        offset = p * bytes_per_player
        segment = board[offset : offset + bytes_per_player]
        value = int.from_bytes(segment, "little")
        players_list.append((p, value))
    return players_list


def identifier(n: int, players: int, board: bytes, *, detail: bool = False) -> str:
    bn = int.from_bytes(board, "little")
    stats = pstats(n, players, board)
    i = f"{n}-{players}-{bn}"
    if detail:
        i += "/" + "/".join(f"{p}:{v}" for p, v in stats)
    return i


if __name__ == "__main__":
    n = 3
    players = 2

    b = new_board(n, players)

    b = move(b, n, players, 0, 0, 0)
    b = move(b, n, players, 1, 1, 1)
    b = move(b, n, players, 1, 2, 2)
    b = move(b, n, players, 0, 0, 1)
    b = move(b, n, players, 0, 0, 2)

    print(render(b, n, players))
    print("winner:", winner(b, n, players))
    bits = n * n
    bytes_per_player = ceil(bits / 8)
    bint = int.from_bytes(b, "little")
    print("board:", bint, "({:0{}b})".format(bint, bits))
    print(f"identifier: {identifier(n, players, b, detail=True)}")
