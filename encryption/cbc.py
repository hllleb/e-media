"""Cipher Block Chaining mode over raw RSA blocks."""

from __future__ import annotations

import secrets

from rsa.padding import pad_pkcs7, unpad_pkcs7
from rsa.rsa_cipher import RSACipher


class CBCEncryptor:
    """
    RSA-CBC: PKCS#7-padded plaintext, XOR with previous ciphertext prefix.

    IV length equals ``plaintext_block_size``.
    """

    def __init__(self, cipher: RSACipher, iv: bytes | None = None) -> None:
        self.cipher = cipher
        self.block_size = cipher.plaintext_block_size
        self.iv = iv

    def _xor(self, a: bytes, b: bytes) -> bytes:
        return bytes(x ^ y for x, y in zip(a, b))

    def generate_iv(self) -> bytes:
        return secrets.token_bytes(self.block_size)

    @property
    def iv_bytes(self) -> bytes:
        if self.iv is None:
            raise ValueError("IV not set.")
        return self.iv

    def encrypt(self, plaintext: bytes, iv: bytes | None = None) -> tuple[bytes, bytes]:
        """Encrypt *plaintext*; returns ``(ciphertext, iv_used)``."""
        iv_used = iv if iv is not None else (self.iv or self.generate_iv())
        if len(iv_used) != self.block_size:
            raise ValueError(
                f"IV must be {self.block_size} bytes, got {len(iv_used)}."
            )

        padded = pad_pkcs7(plaintext, self.block_size)
        prev = iv_used
        out: list[bytes] = []
        for i in range(0, len(padded), self.block_size):
            block = padded[i : i + self.block_size]
            mixed = self._xor(block, prev)
            ct = self.cipher.encrypt_block(mixed)
            out.append(ct)
            prev = ct[: self.block_size]
        return b"".join(out), iv_used

    def decrypt(self, ciphertext: bytes, iv: bytes) -> bytes:
        """Decrypt CBC ciphertext with the given IV."""
        k = self.cipher.modulus_bytes
        if len(ciphertext) % k != 0:
            raise ValueError(
                f"Ciphertext length ({len(ciphertext)}) is not a multiple of "
                f"RSA block size ({k})."
            )
        if len(iv) != self.block_size:
            raise ValueError(
                f"IV must be {self.block_size} bytes, got {len(iv)}."
            )

        prev = iv
        plain_blocks: list[bytes] = []
        for i in range(0, len(ciphertext), k):
            ct = ciphertext[i : i + k]
            decrypted = self.cipher.decrypt_block(ct)
            plain_blocks.append(self._xor(decrypted, prev))
            prev = ct[: self.block_size]
        return unpad_pkcs7(b"".join(plain_blocks))
