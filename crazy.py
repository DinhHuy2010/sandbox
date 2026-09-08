import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id


# ==========================================
# 1. ENCRYPTION HELPER
# ==========================================
def encrypt_with_password(password: str, plaintext: bytes) -> bytes:
    # Generate a fresh 16-byte salt and 12-byte nonce
    salt = os.urandom(16)
    nonce = os.urandom(12)

    # Derive key using Argon2id
    kdf = Argon2id(salt=salt, length=32, iterations=3, lanes=4, memory_cost=65536)
    key = kdf.derive(password.encode())

    # Encrypt
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    # Pack parameters together: [16-byte Salt] + [12-byte Nonce] + [Ciphertext]
    return salt + nonce + ciphertext


# ==========================================
# 2. DECRYPTION HELPER
# ==========================================
def decrypt_with_password(password: str, payload: bytes) -> bytes:
    # Unpack parameters from the payload
    salt = payload[:16]
    nonce = payload[16:28]
    ciphertext = payload[28:]

    # Re-derive the key using the SAVED salt and PROVIDED password
    kdf = Argon2id(salt=salt, length=32, iterations=3, lanes=4, memory_cost=65536)
    key = kdf.derive(password.encode())

    # Decrypt
    aesgcm = AESGCM(key)

    try:
        # AESGCM will throw InvalidTag if password is WRONG or payload was TAMPERED
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
        return plaintext
    except InvalidTag:
        raise ValueError("Decryption failed! Incorrect password or corrupted payload.")


# ==========================================
# USAGE EXAMPLE
# ==========================================
password_input = "MyStrongPassword123!"
secret_message = b"Top secret data stored inside Python."

# Encrypt
encrypted_payload = encrypt_with_password(password_input, secret_message)
print(f"Encrypted Payload Size: {len(encrypted_payload)} bytes")

# Decrypt with CORRECT Password
decrypted = decrypt_with_password("MyStrongPassword123!", encrypted_payload)
print(f"Decrypted Result: {decrypted.decode()}")

# Decrypt with WRONG Password (Fails safely)
try:
    decrypt_with_password("WrongPassword!", encrypted_payload)
except ValueError as e:
    print(f"Caught Expected Error: {e}")
