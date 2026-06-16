"""Tests for PNG signature validation."""

import pytest

from png_parser.reader import PNGReader
from png_parser.signature import PNG_SIGNATURE, PNGSignature


def test_valid_signature():
    sig = PNGSignature(PNG_SIGNATURE)
    assert sig.is_valid
    sig.validate()  # must not raise


def test_invalid_signature_raises():
    sig = PNGSignature(b"\x89PNG\r\n\x1a\x00")
    assert not sig.is_valid
    with pytest.raises(ValueError, match="Invalid PNG signature"):
        sig.validate()


def test_signature_wrong_length_raises():
    with pytest.raises(ValueError, match="exactly 8 bytes"):
        PNGSignature(b"short")


def test_signature_from_reader(tmp_path):
    path = tmp_path / "sig.png"
    path.write_bytes(PNG_SIGNATURE + b"rest")
    reader = PNGReader(str(path))
    sig = PNGSignature.from_reader(reader)
    assert sig.is_valid
    assert reader.pos == 8
