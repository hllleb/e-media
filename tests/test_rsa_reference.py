"""Compare own RSA encryption with independent raw RSA reference."""

from __future__ import annotations

import secrets

import pytest

from encryption import CBCEncryptor, ECBEncryptor
from rsa import RSACipher, generate_keypair

from rsa_reference import (
    ReferenceUnavailableError,
    compare_plaintext_encryption,
    compare_plaintext_encryption_cbc,
    encrypt_raw_ecb_reference,
)


@pytest.fixture(scope="module")
def keypair():
    return generate_keypair(bits=1024)


def test_reference_roundtrip(keypair):
    plaintext = b"PNG IDAT reference compare test data"
    ref_ct = encrypt_raw_ecb_reference(keypair, plaintext)
    k = (keypair.n.bit_length() + 7) // 8
    assert len(ref_ct) % k == 0


def test_own_and_reference_ecb_match(keypair):
    plaintext = b"A" * 100 + b"B" * 50
    own_ct = ECBEncryptor(RSACipher(keypair)).encrypt(plaintext)
    result = compare_plaintext_encryption(keypair, plaintext, own_ct)
    assert result.blocks_compared > 0
    assert result.all_match
    assert result.matching_blocks == result.blocks_compared


def test_own_and_reference_cbc_match(keypair):
    plaintext = b"CBC compare test data for PNG IDAT payload"
    iv = secrets.token_bytes(keypair.plaintext_block_size)
    own_ct, _ = CBCEncryptor(RSACipher(keypair)).encrypt(plaintext, iv=iv)
    result = compare_plaintext_encryption_cbc(keypair, plaintext, iv, own_ct)
    assert result.all_match


def test_reference_unavailable_message():
    assert ReferenceUnavailableError is not None
