"""Tests for PNGParser and chunk offsets."""

import pytest

from png_parser import PNGParser
from tests.conftest import build_png, make_chunk


def test_parse_rgb_png(rgb_png_path):
    png = PNGParser().parse(rgb_png_path)
    assert png.signature.is_valid
    assert len(png.chunks) == 3
    ihdr = png.get_ihdr()
    assert ihdr.width == 8
    assert ihdr.height == 8


def test_chunk_offsets_recorded(rich_png_path):
    png = PNGParser().parse(rich_png_path)
    assert len(png.chunks_pos) == len(png.chunks)
    start, end = png.chunks_pos[0]
    assert start == 8  # first byte after signature
    assert end > start
    assert png.get_chunk_offset(0) == (start, end)


def test_trailing_bytes_detected(rich_png_path):
    png = PNGParser().parse(rich_png_path)
    assert png.trailing_bytes == b"HIDDEN_AFTER_IEND"


def test_parse_file_not_found():
    with pytest.raises(FileNotFoundError):
        PNGParser().parse("nonexistent_file.png")


def test_parse_invalid_signature(tmp_path):
    path = tmp_path / "bad.png"
    path.write_bytes(b"NOT_A_PNG\x00" + b"\x00" * 20)
    with pytest.raises(ValueError, match="Invalid PNG signature"):
        PNGParser().parse(str(path))


def test_parse_truncated_chunk(tmp_path):
    path = tmp_path / "trunc.png"
    path.write_bytes(build_png()[:20])
    with pytest.raises(EOFError):
        PNGParser().parse(str(path))


def test_ancillary_chunks_decoded(rich_png_path):
    png = PNGParser().parse(rich_png_path)
    ancillary = png.get_ancillary_chunks()
    types = {c.type_code for c in ancillary}
    assert types == {"gAMA", "sRGB", "pHYs", "tIME", "tEXt"}
