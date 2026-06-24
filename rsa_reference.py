"""Reference raw RSA encryption for comparison (independent pow(m, e, n))."""

from __future__ import annotations

from dataclasses import dataclass

from encryption.ecb import ECBEncryptor
from rsa import RSAKeyPair, RSACipher
from rsa.padding import pad_pkcs7, unpad_pkcs7

try:
    from Crypto.PublicKey import RSA
except ImportError:  # pragma: no cover
    RSA = None  # type: ignore[misc, assignment]


class ReferenceUnavailableError(ImportError):
    """Raised when PyCryptodome is not installed."""


def _require_pycryptodome():
    if RSA is None:
        raise ReferenceUnavailableError(
            "PyCryptodome is required for reference comparison. "
            "Install with: pip install pycryptodome"
        )


def reference_public_key(key: RSAKeyPair):
    """Build a PyCryptodome key from our material (for optional OAEP demos)."""
    _require_pycryptodome()
    return RSA.construct((key.n, key.e, key.d))


@dataclass
class CompareResult:
    blocks_compared: int
    matching_blocks: int
    all_match: bool
    first_mismatch_index: int | None
    own_ciphertext_len: int
    reference_ciphertext_len: int


def encrypt_raw_ecb_reference(key: RSAKeyPair, plaintext: bytes) -> bytes:
    """
    Independent raw RSA-ECB using pow(m, e, n) on PKCS#7-padded data.

    Must match our ECBEncryptor byte-for-byte when using the same key.
    """
    block_size = key.plaintext_block_size
    modulus_bytes = key.modulus_bytes
    padded = pad_pkcs7(plaintext, block_size)
    out = bytearray()
    for i in range(0, len(padded), block_size):
        block = padded[i : i + block_size]
        m = int.from_bytes(block.ljust(block_size, b"\x00"), "big")
        if m >= key.n:
            raise ValueError("Reference block integer >= modulus.")
        c = pow(m, key.e, key.n)
        out.extend(c.to_bytes(modulus_bytes, "big"))
    return bytes(out)


def decrypt_raw_ecb_reference(key: RSAKeyPair, ciphertext: bytes) -> bytes:
    """Decrypt raw RSA-ECB ciphertext with pow(c, d, n)."""
    block_size = key.plaintext_block_size
    modulus_bytes = key.modulus_bytes
    if len(ciphertext) % modulus_bytes != 0:
        raise ValueError("Invalid reference ciphertext length.")
    plain_blocks: list[bytes] = []
    for i in range(0, len(ciphertext), modulus_bytes):
        ct = ciphertext[i : i + modulus_bytes]
        c = int.from_bytes(ct, "big")
        m = pow(c, key.d, key.n)
        plain_blocks.append(m.to_bytes(block_size, "big"))
    return unpad_pkcs7(b"".join(plain_blocks))


def compare_ciphertext_blocks(
    own_ciphertext: bytes,
    reference_ciphertext: bytes,
    modulus_bytes: int,
) -> CompareResult:
    """Compare fixed-width RSA ciphertext blocks."""
    if len(own_ciphertext) != len(reference_ciphertext):
        blocks = min(len(own_ciphertext), len(reference_ciphertext)) // modulus_bytes
    else:
        blocks = len(own_ciphertext) // modulus_bytes

    matching = 0
    first_mismatch = None
    for i in range(blocks):
        start = i * modulus_bytes
        end = start + modulus_bytes
        if own_ciphertext[start:end] == reference_ciphertext[start:end]:
            matching += 1
        elif first_mismatch is None:
            first_mismatch = i
    return CompareResult(
        blocks_compared=blocks,
        matching_blocks=matching,
        all_match=(
            matching == blocks
            and len(own_ciphertext) == len(reference_ciphertext)
        ),
        first_mismatch_index=first_mismatch,
        own_ciphertext_len=len(own_ciphertext),
        reference_ciphertext_len=len(reference_ciphertext),
    )


def compare_plaintext_encryption(
    key: RSAKeyPair,
    plaintext: bytes,
    own_ciphertext: bytes | None = None,
) -> CompareResult:
    """
    Compare our raw RSA-ECB against an independent pow(m, e, n) reference.

    With raw RSA (no random padding), ciphertext blocks should match exactly.
    """
    if own_ciphertext is None:
        own_ciphertext = ECBEncryptor(RSACipher(key)).encrypt(plaintext)

    ref_ct = encrypt_raw_ecb_reference(key, plaintext)
    modulus_bytes = key.modulus_bytes
    result = compare_ciphertext_blocks(own_ciphertext, ref_ct, modulus_bytes)

    recovered = decrypt_raw_ecb_reference(key, ref_ct)
    if recovered != plaintext:
        raise ValueError("Reference round-trip does not match plaintext.")

    return result


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


def encrypt_raw_cbc_reference(
    key: RSAKeyPair,
    plaintext: bytes,
    iv: bytes,
) -> bytes:
    """Independent raw RSA-CBC; must match CBCEncryptor when IV is the same."""
    block_size = key.plaintext_block_size
    modulus_bytes = key.modulus_bytes
    if len(iv) != block_size:
        raise ValueError(f"IV must be {block_size} bytes, got {len(iv)}.")

    padded = pad_pkcs7(plaintext, block_size)
    prev = iv
    out = bytearray()
    for i in range(0, len(padded), block_size):
        block = padded[i : i + block_size]
        mixed = _xor_bytes(block, prev)
        m = int.from_bytes(mixed.ljust(block_size, b"\x00"), "big")
        if m >= key.n:
            raise ValueError("Reference CBC block integer >= modulus.")
        c = pow(m, key.e, key.n)
        ct = c.to_bytes(modulus_bytes, "big")
        out.extend(ct)
        prev = ct[:block_size]
    return bytes(out)


def decrypt_raw_cbc_reference(
    key: RSAKeyPair,
    ciphertext: bytes,
    iv: bytes,
) -> bytes:
    """Decrypt raw RSA-CBC ciphertext with pow(c, d, n)."""
    block_size = key.plaintext_block_size
    modulus_bytes = key.modulus_bytes
    if len(ciphertext) % modulus_bytes != 0:
        raise ValueError("Invalid reference CBC ciphertext length.")
    if len(iv) != block_size:
        raise ValueError(f"IV must be {block_size} bytes, got {len(iv)}.")

    prev = iv
    plain_blocks: list[bytes] = []
    for i in range(0, len(ciphertext), modulus_bytes):
        ct = ciphertext[i : i + modulus_bytes]
        c = int.from_bytes(ct, "big")
        m = pow(c, key.d, key.n)
        decrypted = m.to_bytes(block_size, "big")
        plain_blocks.append(_xor_bytes(decrypted, prev))
        prev = ct[:block_size]
    return unpad_pkcs7(b"".join(plain_blocks))


def compare_plaintext_encryption_cbc(
    key: RSAKeyPair,
    plaintext: bytes,
    iv: bytes,
    own_ciphertext: bytes | None = None,
) -> CompareResult:
    """
    Compare our raw RSA-CBC against an independent reference implementation.

    Requires the same IV on both sides for byte-identical ciphertext.
    """
    from encryption.cbc import CBCEncryptor

    if own_ciphertext is None:
        own_ciphertext, _ = CBCEncryptor(RSACipher(key)).encrypt(plaintext, iv=iv)

    ref_ct = encrypt_raw_cbc_reference(key, plaintext, iv)
    modulus_bytes = key.modulus_bytes
    result = compare_ciphertext_blocks(own_ciphertext, ref_ct, modulus_bytes)

    recovered = decrypt_raw_cbc_reference(key, ref_ct, iv)
    if recovered != plaintext:
        raise ValueError("Reference CBC round-trip does not match plaintext.")

    return result
