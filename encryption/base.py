"""Shared helpers for block-wise RSA encryption modes."""

from __future__ import annotations


def split_blocks(data: bytes, block_size: int) -> list[bytes]:
    """Split *data* into chunks of at most *block_size* bytes."""
    if block_size <= 0:
        raise ValueError("block_size must be positive.")
    return [data[i : i + block_size] for i in range(0, len(data), block_size)]


def join_blocks(blocks: list[bytes]) -> bytes:
    """Concatenate decrypted plaintext blocks."""
    return b"".join(blocks)
