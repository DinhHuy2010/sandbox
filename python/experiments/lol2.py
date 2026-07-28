def ceaser(text: str, shift: int) -> str:
    result = ""
    for char in text:
        if char.isalpha():
            shift_amount = shift % 26
            if char.islower():
                base = ord("a")
            else:
                base = ord("A")
            shifted_char = chr((ord(char) - base + shift_amount) % 26 + base)
            result += shifted_char
        else:
            result += char
    return result


def unceaser(text: str, shift: int) -> str:
    return ceaser(text, -shift)


def bytes_to_boolarr(byte_data: bytes) -> list[bool]:
    bool_arr = []
    for byte in byte_data:
        for i in range(8):
            bool_arr.append((byte >> (7 - i)) & 1 == 1)
    return bool_arr


def boolarr_to_bytes(bool_arr: list[bool]) -> bytes:
    byte_data = bytearray()
    for i in range(0, len(bool_arr), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bool_arr) and bool_arr[i + j]:
                byte |= 1 << (7 - j)
        byte_data.append(byte)
    return bytes(byte_data)


print(bytes_to_boolarr(b"hello"))
