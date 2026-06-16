"""Tests for Chunk base class and chunk factory."""

import zlib

import pytest

from png_parser.chunk import GenericChunk
from png_parser.chunks import chunk_factory
from png_parser.chunks.ancillary import (
    GammaChunk,
    PhysicalPixelDimensionsChunk,
    TextChunk,
    TimeChunk,
)
from png_parser.chunks.critical import IHDRChunk, IDATChunk, IENDChunk


def _crc(type_code: str, data: bytes) -> int:
    return zlib.crc32(type_code.encode() + data) & 0xFFFFFFFF


def test_ihdr_chunk_flags_and_fields():
    import struct

    data = struct.pack(">IIBBBBB", 100, 50, 8, 2, 0, 0, 0)
    chunk = IHDRChunk(13, "IHDR", data, _crc("IHDR", data))
    assert chunk.is_critical
    assert chunk.is_public
    assert chunk.crc_valid
    assert chunk.width == 100
    assert chunk.height == 50
    assert chunk.color_type_name == "RGB (Truecolor)"


def test_ancillary_chunk_flags():
    data = b"Author\x00Alice"
    chunk = TextChunk(len(data), "tEXt", data, _crc("tEXt", data))
    assert chunk.is_ancillary
    assert chunk.is_safe_to_copy
    assert chunk.keyword == "Author"
    assert chunk.text == "Alice"


def test_gamma_chunk_decode():
    import struct

    data = struct.pack(">I", 45455)
    chunk = GammaChunk(4, "gAMA", data, _crc("gAMA", data))
    assert abs(chunk.gamma - 0.45455) < 0.00001


def test_phys_chunk_dpi():
    import struct

    data = struct.pack(">IIB", 3937, 3937, 1)
    chunk = PhysicalPixelDimensionsChunk(9, "pHYs", data, _crc("pHYs", data))
    assert chunk.dpi_x is not None
    assert 99 < chunk.dpi_x < 101


def test_time_chunk_datetime():
    import struct

    data = struct.pack(">HBBBBB", 2024, 6, 15, 10, 30, 0)
    chunk = TimeChunk(7, "tIME", data, _crc("tIME", data))
    assert chunk.year == 2024
    assert chunk.month == 6
    assert "2024-06-15" in chunk.as_datetime.isoformat()


def test_idat_and_iend():
    idat = IDATChunk(5, "IDAT", b"\x78\x9c\xed", _crc("IDAT", b"\x78\x9c\xed"))
    assert idat.compressed_data == b"\x78\x9c\xed"
    iend = IENDChunk(0, "IEND", b"", _crc("IEND", b""))
    assert iend.length == 0


def test_generic_chunk_for_unknown_type():
    data = b"custom"
    chunk = chunk_factory("zzZZ", 6, data, _crc("zzZZ", data))
    assert isinstance(chunk, GenericChunk)
    assert chunk.type_code == "zzZZ"


def test_chunk_to_bytes_roundtrip():
    import struct

    data = struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)
    crc = _crc("IHDR", data)
    chunk = IHDRChunk(13, "IHDR", data, crc)
    raw = chunk.to_bytes()
    assert raw[:4] == (13).to_bytes(4, "big")
    assert raw[4:8] == b"IHDR"
    assert raw[8:-4] == data
    assert int.from_bytes(raw[-4:], "big") == crc


def test_invalid_crc_detected():
    data = b"Author\x00Bob"
    chunk = TextChunk(len(data), "tEXt", data, 0xDEADBEEF)
    assert not chunk.crc_valid
