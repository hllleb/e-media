"""Unit tests for ECB and CBC encryption modes."""

from __future__ import annotations

import secrets

import pytest

from encryption import CBCEncryptor, ECBEncryptor
from rsa import RSACipher, generate_keypair


@pytest.fixture(scope="module")
def keypair():
    return generate_keypair(bits=1024)


@pytest.fixture(scope="module")
def cipher(keypair):
    return RSACipher(keypair)


def test_ecb_roundtrip(cipher):
    ecb = ECBEncryptor(cipher)
    data = secrets.token_bytes(cipher.plaintext_block_size * 3 + 17)
    ct = ecb.encrypt(data)
    assert ecb.decrypt(ct) == data


def test_ecb_identical_blocks_same_ciphertext(cipher):
    """Raw RSA-ECB: identical PKCS#7 plaintext blocks -> identical ciphertext."""
    ecb = ECBEncryptor(cipher)
    block = b"A" * cipher.plaintext_block_size
    data = block + block
    ct = ecb.encrypt(data)
    k = cipher.modulus_bytes
    # PKCS#7 adds one extra padding block when len is already a multiple of block_size.
    assert len(ct) == 3 * k
    assert ecb.decrypt(ct) == data
    assert ct[:k] == ct[k : 2 * k]


def test_cbc_roundtrip(cipher):
    cbc = CBCEncryptor(cipher)
    data = secrets.token_bytes(cipher.plaintext_block_size * 2 + 5)
    ct, iv = cbc.encrypt(data)
    assert cbc.decrypt(ct, iv) == data


def test_cbc_different_iv_different_ciphertext(cipher):
    cbc = CBCEncryptor(cipher)
    data = b"repeatable plaintext block for CBC test!!"
    data = data.ljust(cipher.plaintext_block_size * 2, b"\x00")
    ct1, iv1 = cbc.encrypt(data, iv=secrets.token_bytes(cipher.plaintext_block_size))
    ct2, iv2 = cbc.encrypt(data, iv=secrets.token_bytes(cipher.plaintext_block_size))
    assert iv1 != iv2
    assert ct1 != ct2


def test_cbc_wrong_iv_fails(cipher):
    from rsa.padding import PaddingError

    cbc = CBCEncryptor(cipher)
    data = b"small"
    ct, iv = cbc.encrypt(data)
    bad_iv = secrets.token_bytes(cipher.plaintext_block_size)
    try:
        assert cbc.decrypt(ct, bad_iv) != data
    except PaddingError:
        pass  # wrong IV often corrupts PKCS#7 padding


def test_ecb_invalid_ciphertext_length(cipher):
    ecb = ECBEncryptor(cipher)
    with pytest.raises(ValueError):
        ecb.decrypt(b"\x00" * (cipher.modulus_bytes + 1))
