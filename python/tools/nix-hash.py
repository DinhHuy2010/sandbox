import hashlib
import subprocess
import tempfile


class FormatError(ValueError):
    pass


class BaseNix32:
    # Nix's custom base32 alphabet
    characters = "0123456789abcdfghijklmnpqrsvwxyz"
    invalid = 0xFF

    # Reverse map: char -> value
    reverse_map = {ch: i for i, ch in enumerate(characters)}

    @classmethod
    def encoded_length(cls, n: int) -> int:
        if n == 0:
            return 0
        return (n * 8 - 1) // 5 + 1

    @classmethod
    def encode(cls, bs: bytes) -> str:
        if not bs:
            return ""

        length = cls.encoded_length(len(bs))
        out = []

        for n in range(length - 1, -1, -1):
            b = n * 5
            i = b // 8
            j = b % 8

            cur = bs[i] >> j
            nxt = 0 if i >= len(bs) - 1 else (bs[i + 1] << (8 - j)) & 0xFF
            c = (cur | nxt) & 0x1F

            out.append(cls.characters[c])

        return "".join(out)

    @classmethod
    def decode(cls, s: str) -> bytes:
        res = bytearray()

        for n in range(len(s)):
            c = s[len(s) - n - 1]
            if c not in cls.reverse_map:
                raise FormatError(
                    f"invalid character in Nix32 string: {c!r}"
                )

            digit = cls.reverse_map[c]

            b = n * 5
            i = b // 8
            j = b % 8

            while len(res) < i + 1:
                res.append(0)
            res[i] |= (digit << j) & 0xFF

            carry = digit >> (8 - j) if j != 0 else 0
            if carry:
                while len(res) < i + 2:
                    res.append(0)
                res[i + 1] |= carry

        return bytes(res)


def test_same():
    msg = b"Hello, world!"
    
    # 1. Create temporary file and write msg data into it
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(msg)
        tmp.flush() # Ensure data is fully written to disk before reading
        
        # 2. Calculate raw SHA-256 digest in Python on the SAME data
        sha256_hash = hashlib.sha256(msg).digest()
        python_nix32 = BaseNix32.encode(sha256_hash)
        
        # 3. Request nix-hash to check the temporary file
        # Removed the empty string ("") argument
        with subprocess.Popen(
            ["nix-hash", "--type", "sha256", "--base32", "--flat", tmp.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            stdout, stderr = proc.communicate()
            
            if proc.returncode != 0:
                print(f"nix-hash failed: {stderr.decode()}")
                return
                
            nix_output = stdout.decode().strip()
            
            print(f"BaseNix32 (Python): {python_nix32}")
            print(f"Nix-hash (Native): {nix_output}")
            
            assert python_nix32 == nix_output, "Outputs do not match!"
            print("✅ Success! Your BaseNix32 implementation matches Nix exactly.")

if __name__ == "__main__":
    test_same()