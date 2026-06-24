"""PKCS#7 block padding for raw RSA."""

from __future__ import annotations


class PaddingError(ValueError):
    """Invalid PKCS#7 padding."""


def raw_plaintext_block_size(modulus_bits: int) -> int:
    """
    Maximum plaintext bytes per RSA block ensuring m < n.

    Uses (bit_length - 1) // 8 so int.from_bytes(block) < n.
    """
    return (modulus_bits - 1) // 8


def pad_pkcs7(data: bytes, block_size: int) -> bytes:
    """Pad *data* to a multiple of *block_size* using PKCS#7."""
    if block_size <= 0 or block_size > 255:
        raise ValueError("block_size must be between 1 and 255.")
    padding_len = block_size - (len(data) % block_size)
    if padding_len == 0:
        padding_len = block_size
    return data + bytes([padding_len] * padding_len)


def unpad_pkcs7(padded: bytes) -> bytes:
    """Remove PKCS#7 padding."""
    if not padded:
        raise PaddingError("Cannot unpad empty data.")
    padding_len = padded[-1]
    if padding_len <= 0 or padding_len > len(padded):
        raise PaddingError("Invalid PKCS#7 padding length.")
    if padded[-padding_len:] != bytes([padding_len] * padding_len):
        raise PaddingError("Invalid PKCS#7 padding bytes.")
    return padded[:-padding_len]
