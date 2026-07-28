def compress(text: bytes) -> bytes:
    """Compresses the given text using a simple run-length encoding algorithm."""
    if not text:
        return b""

    compressed = bytearray()
    count = 1
    previous_byte = text[0]

    for current_byte in text[1:]:
        if current_byte == previous_byte and count < 255:
            count += 1
        else:
            compressed.append(count)
            compressed.append(previous_byte)
            previous_byte = current_byte
            count = 1

    # Append the last run
    compressed.append(count)
    compressed.append(previous_byte)

    return bytes(compressed)


def decompress(compressed: bytes) -> bytes:
    """Decompresses the given compressed text using the run-length encoding algorithm."""
    if not compressed:
        return b""

    decompressed = bytearray()

    for i in range(0, len(compressed), 2):
        count = compressed[i]
        byte = compressed[i + 1]
        decompressed.extend([byte] * count)

    return bytes(decompressed)


print(compress(b"aaabbbcccdde"))
print(decompress(compress(b"aaabbbcccdde")))
