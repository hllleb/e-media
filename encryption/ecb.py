"""Electronic Codebook mode – raw RSA, PKCS#7-padded plaintext."""

from __future__ import annotations

from rsa.padding import pad_pkcs7, unpad_pkcs7
from rsa.rsa_cipher import RSACipher


class ECBEncryptor:
    """
    RSA-ECB.

    Identical PKCS#7 plaintext blocks produce identical ciphertext blocks.
    """

    def __init__(self, cipher: RSACipher) -> None:
        self.cipher = cipher
        self.block_size = cipher.plaintext_block_size

    def encrypt(self, plaintext: bytes) -> bytes:
        padded = pad_pkcs7(plaintext, self.block_size)
        out: list[bytes] = []
        for i in range(0, len(padded), self.block_size):
            block = padded[i : i + self.block_size]
            out.append(self.cipher.encrypt_block(block))
        return b"".join(out)

    def decrypt(self, ciphertext: bytes) -> bytes:
        k = self.cipher.modulus_bytes
        if len(ciphertext) % k != 0:
            raise ValueError(
                f"Ciphertext length ({len(ciphertext)}) is not a multiple of "
                f"RSA block size ({k})."
            )
        plain_blocks: list[bytes] = []
        for i in range(0, len(ciphertext), k):
            plain_blocks.append(self.cipher.decrypt_block(ciphertext[i : i + k]))
        return unpad_pkcs7(b"".join(plain_blocks))
