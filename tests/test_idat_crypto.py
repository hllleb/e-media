"""Integration tests for IDAT encryption/decryption."""

from __future__ import annotations

import pytest

from idat_processor import (
    BlockMode,
    DataVariant,
    decrypt_idat,
    encrypt_idat,
    roundtrip_plaintext,
)
from png_parser import PNGParser
from rsa import generate_keypair


@pytest.fixture(scope="module")
def keypair():
    return generate_keypair(bits=1024)


@pytest.fixture
def small_png_bytes():
    from tests.conftest import build_png

    return build_png(width=8, height=8)


@pytest.fixture
def small_png_path(tmp_path, small_png_bytes):
    path = tmp_path / "tiny.png"
    path.write_bytes(small_png_bytes)
    return str(path)


@pytest.mark.parametrize("variant", [DataVariant.FILTERED, DataVariant.COMPRESSED])
@pytest.mark.parametrize("mode", [BlockMode.ECB, BlockMode.CBC])
def test_idat_roundtrip(small_png_path, keypair, variant, mode):
    png = PNGParser().parse(small_png_path)
    original = (
        png.get_filtered_idat_bytes()
        if variant == DataVariant.FILTERED
        else png.get_idat_compressed()
    )

    enc = encrypt_idat(png, keypair, mode=mode, variant=variant)
    dec = decrypt_idat(enc.png, keypair, mode=mode, variant=variant, iv=enc.iv)

    assert dec.plaintext == original


def test_encrypted_png_keeps_ihdr(small_png_path, keypair):
    png = PNGParser().parse(small_png_path)
    ihdr_before = png.get_ihdr()
    enc = encrypt_idat(
        png,
        keypair,
        mode=BlockMode.ECB,
        variant=DataVariant.FILTERED,
    )
    ihdr_after = enc.png.get_ihdr()
    assert ihdr_after.width == ihdr_before.width
    assert ihdr_after.height == ihdr_before.height
    assert ihdr_after.raw_data == ihdr_before.raw_data


def test_only_idat_changes(small_png_path, keypair):
    png = PNGParser().parse(small_png_path)
    enc = encrypt_idat(
        png,
        keypair,
        mode=BlockMode.ECB,
        variant=DataVariant.FILTERED,
    )
    before_types = [c.type_code for c in png.chunks if c.type_code != "IDAT"]
    after_types = [c.type_code for c in enc.png.chunks if c.type_code != "IDAT"]
    assert before_types == after_types
    assert png.get_idat_compressed() != enc.png.get_idat_compressed()


def test_variants_not_equivalent(small_png_path, keypair):
    png = PNGParser().parse(small_png_path)
    filtered = roundtrip_plaintext(
        png, keypair, mode=BlockMode.ECB, variant=DataVariant.FILTERED
    )
    compressed = roundtrip_plaintext(
        png, keypair, mode=BlockMode.ECB, variant=DataVariant.COMPRESSED
    )
    assert filtered != compressed
