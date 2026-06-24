"""End-to-end Project 2 tests on repository sample images."""

from __future__ import annotations

from pathlib import Path

import pytest

from idat_processor import BlockMode, DataVariant, decrypt_idat, encrypt_idat
from png_parser import PNGParser
from rsa import generate_keypair, save_keypair

IMAGES = Path(__file__).resolve().parent.parent / "images"
# Limit plaintext so RSA tests stay fast on large sample files.
MAX_BYTES = 512


@pytest.fixture(scope="module")
def repo_key(tmp_path_factory):
    key = generate_keypair(bits=1024)
    path = tmp_path_factory.mktemp("keys") / "test_key.json"
    save_keypair(key, path)
    return key, str(path)


@pytest.mark.parametrize(
    "image_name",
    ["rgb.png", "palette.png"],
)
@pytest.mark.parametrize("variant", [DataVariant.FILTERED, DataVariant.COMPRESSED])
@pytest.mark.parametrize("mode", [BlockMode.ECB, BlockMode.CBC])
def test_repo_image_roundtrip(repo_key, image_name, variant, mode):
    key, _ = repo_key
    path = IMAGES / image_name
    if not path.exists():
        pytest.skip(f"{path} not found")

    png = PNGParser().parse(str(path))
    original = (
        png.get_filtered_idat_bytes()
        if variant == DataVariant.FILTERED
        else png.get_idat_compressed()
    )
    original = original[:MAX_BYTES]

    enc = encrypt_idat(
        png,
        key,
        mode=mode,
        variant=variant,
        max_bytes=MAX_BYTES,
    )
    dec = decrypt_idat(
        enc.png,
        key,
        mode=mode,
        variant=variant,
        iv=enc.iv,
    )
    assert dec.plaintext == original
