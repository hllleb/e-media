"""Unit tests for own RSA implementation."""

from __future__ import annotations

import secrets

import pytest

from rsa import RSACipher, generate_keypair
from rsa.padding import PaddingError, pad_pkcs7, unpad_pkcs7
from rsa.primes import is_probable_prime


@pytest.fixture(scope="module")
def keypair():
    return generate_keypair(bits=1024)


@pytest.fixture(scope="module")
def cipher(keypair):
    return RSACipher(keypair)


def test_miller_rabin_known_primes():
    assert is_probable_prime(2)
    assert is_probable_prime(65537)
    assert not is_probable_prime(4)
    assert not is_probable_prime(561)


def test_keypair_inverse(keypair):
    phi = (keypair.p - 1) * (keypair.q - 1)
    assert (keypair.e * keypair.d) % phi == 1


def test_pkcs7_roundtrip():
    msg = b"hello raw RSA padding test"
    padded = pad_pkcs7(msg, 16)
    assert len(padded) % 16 == 0
    assert unpad_pkcs7(padded) == msg


def test_pkcs7_invalid_padding():
    with pytest.raises(PaddingError):
        unpad_pkcs7(b"\x05" * 4)


def test_encrypt_decrypt_block(cipher):
    msg = secrets.token_bytes(32)
    ct = cipher.encrypt_block(msg)
    assert len(ct) == cipher.modulus_bytes
    decrypted = cipher.decrypt_block(ct)
    assert decrypted[: len(msg)] == msg


def test_full_block_size(cipher):
    msg = secrets.token_bytes(cipher.plaintext_block_size)
    ct = cipher.encrypt_block(msg)
    assert cipher.decrypt_block(ct) == msg


def test_message_too_long(cipher):
    too_long = b"x" * (cipher.plaintext_block_size + 1)
    with pytest.raises(ValueError):
        cipher.encrypt_block(too_long)


def test_keypair_json_roundtrip(keypair, tmp_path):
    from rsa.keys import load_keypair, save_keypair

    path = tmp_path / "key.json"
    save_keypair(keypair, path)
    loaded = load_keypair(path)
    assert loaded.n == keypair.n
    assert loaded.e == keypair.e
    assert loaded.d == keypair.d
