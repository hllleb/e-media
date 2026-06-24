"""Raw RSA encryption and decryption: c = m^e mod n (no PKCS#1 encryption padding)."""

from __future__ import annotations

from .keys import RSAKeyPair
from .padding import raw_plaintext_block_size


class RSACipher:
    """
    Raw RSA on fixed-width plaintext blocks.

    Each block is zero-padded to ``plaintext_block_size`` bytes, interpreted as
    a big-endian integer m < n, then encrypted with pow(m, e, n).
    """

    def __init__(self, key: RSAKeyPair) -> None:
        self.key = key
        self.modulus_bytes = key.modulus_bytes
        self.plaintext_block_size = key.plaintext_block_size

    # Backward-compatible alias used in tests / older code paths.
    @property
    def max_block_size(self) -> int:
        return self.plaintext_block_size

    def encrypt_int(self, message: int) -> int:
        if message >= self.key.n:
            raise ValueError(f"Message integer must be < n, got {message} >= {self.key.n}.")
        return pow(message, self.key.e, self.key.n)

    def decrypt_int(self, ciphertext: int) -> int:
        return pow(ciphertext, self.key.d, self.key.n)

    def _normalize_plaintext_block(self, block: bytes) -> bytes:
        if len(block) > self.plaintext_block_size:
            raise ValueError(
                f"Plaintext block too long ({len(block)} > {self.plaintext_block_size})."
            )
        return block.ljust(self.plaintext_block_size, b"\x00")

    def encrypt_block(self, plaintext: bytes) -> bytes:
        """Encrypt a single raw RSA block, returning fixed-width ciphertext."""
        block = self._normalize_plaintext_block(plaintext)
        m = int.from_bytes(block, "big")
        c = self.encrypt_int(m)
        return c.to_bytes(self.modulus_bytes, "big")

    def decrypt_block(self, ciphertext: bytes) -> bytes:
        """Decrypt a single RSA block, returning fixed-width plaintext bytes."""
        if len(ciphertext) != self.modulus_bytes:
            raise ValueError(
                f"Ciphertext block must be {self.modulus_bytes} bytes, "
                f"got {len(ciphertext)}."
            )
        c = int.from_bytes(ciphertext, "big")
        m = self.decrypt_int(c)
        return m.to_bytes(self.plaintext_block_size, "big")


def plaintext_block_size_for_modulus(n: int) -> int:
    """Helper: raw plaintext block size for modulus *n*."""
    return raw_plaintext_block_size(n.bit_length())
