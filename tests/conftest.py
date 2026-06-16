"""Shared fixtures and PNG builders for unit tests."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

import pytest

from png_parser.image_data import ImageHeaderParams, apply_filter, row_byte_length

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

_ADAM7_PASSES = (
    (0, 0, 8, 8),
    (4, 0, 8, 8),
    (0, 4, 4, 8),
    (2, 0, 4, 4),
    (0, 2, 2, 4),
    (1, 0, 2, 2),
    (0, 1, 1, 2),
)


def make_chunk(type_code: str, data: bytes) -> bytes:
    payload = type_code.encode("ascii") + data
    return (
        struct.pack(">I", len(data))
        + payload
        + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
    )


def make_ihdr(
    width: int,
    height: int,
    bit_depth: int = 8,
    color_type: int = 2,
    interlace: int = 0,
) -> bytes:
    return struct.pack(
        ">IIBBBBB", width, height, bit_depth, color_type, 0, 0, interlace
    )


def encode_interlaced_rows(
    header: ImageHeaderParams, rows: list[bytes], filter_type: int = 0
) -> bytes:
    """Build filtered Adam7 byte stream from full-width grayscale rows."""
    out = bytearray()
    for x_start, y_start, x_step, y_step in _ADAM7_PASSES:
        if x_start >= header.width:
            continue
        pixels_per_row = int(math.ceil((header.width - x_start) / x_step))
        prev: bytes | None = None
        for y in range(y_start, header.height, y_step):
            samples = []
            for i in range(pixels_per_row):
                x = x_start + i * x_step
                if x < header.width:
                    samples.append(rows[y][x])
            pass_row = bytes(samples)
            filtered = apply_filter(header, filter_type, pass_row, prev)
            out.append(filter_type)
            out.extend(filtered)
            prev = pass_row
    return bytes(out)


def build_png(
    *,
    width: int = 8,
    height: int = 8,
    bit_depth: int = 8,
    color_type: int = 2,
    interlace: int = 0,
    idat_payload: bytes | None = None,
    palette: bytes | None = None,
    ancillary: list[tuple[str, bytes]] | None = None,
    trailing: bytes = b"",
) -> bytes:
    """Assemble a minimal valid PNG byte string."""
    parts = [PNG_SIGNATURE, make_chunk("IHDR", make_ihdr(width, height, bit_depth, color_type, interlace))]

    if palette is not None:
        parts.append(make_chunk("PLTE", palette))

    for type_code, data in ancillary or []:
        parts.append(make_chunk(type_code, data))

    if idat_payload is None:
        if color_type == 2 and bit_depth == 8:
            row = b"\x00" + bytes([255, 0, 0] * width)
            idat_payload = zlib.compress(row * height)
        elif color_type == 0 and bit_depth == 8 and interlace == 0:
            row = b"\x00" + bytes([128] * width)
            idat_payload = zlib.compress(row * height)
        else:
            raise ValueError("Provide idat_payload for this image configuration.")

    parts.append(make_chunk("IDAT", idat_payload))
    parts.append(make_chunk("IEND", b""))
    return b"".join(parts) + trailing


@pytest.fixture
def tmp_png(tmp_path: Path):
    """Return a callable that writes a PNG to *tmp_path* and returns its path."""

    def _write(name: str, png_bytes: bytes) -> str:
        path = tmp_path / name
        path.write_bytes(png_bytes)
        return str(path)

    return _write


@pytest.fixture
def rgb_png_path(tmp_png):
    return tmp_png("rgb.png", build_png(width=8, height=8))


@pytest.fixture
def palette_png_path(tmp_png):
    plte = bytes([255, 0, 0, 0, 0, 255])
    rows = b"".join(b"\x00" + bytes([0, 1, 0, 1]) for _ in range(4))
    png = build_png(
        width=4,
        height=4,
        color_type=3,
        palette=plte,
        idat_payload=zlib.compress(rows),
    )
    return tmp_png("palette.png", png)


@pytest.fixture
def rich_png_path(tmp_png):
    ancillary = [
        ("gAMA", struct.pack(">I", 45455)),
        ("sRGB", b"\x00"),
        ("pHYs", struct.pack(">IIB", 3937, 3937, 1)),
        ("tIME", struct.pack(">HBBBBB", 2024, 5, 31, 12, 0, 0)),
        ("tEXt", b"Software\x00unit-test"),
    ]
    png = build_png(ancillary=ancillary, trailing=b"HIDDEN_AFTER_IEND")
    return tmp_png("rich.png", png)


@pytest.fixture
def interlaced_png_path(tmp_png):
    width = height = 8
    rows = [bytes([((x + y) % 2) * 255 for x in range(width)]) for y in range(height)]
    header = ImageHeaderParams(width, height, 8, 0, 1)
    filtered = encode_interlaced_rows(header, rows)
    png = build_png(
        width=width,
        height=height,
        color_type=0,
        interlace=1,
        idat_payload=zlib.compress(filtered),
    )
    return tmp_png("interlaced.png", png)
