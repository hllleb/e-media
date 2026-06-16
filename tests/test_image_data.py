"""Tests for image_data module (filters, BitArray, interlace)."""

import struct

import pytest

from png_parser.image_data import (
    BitArray,
    ImageData,
    ImageHeaderParams,
    apply_filter,
    filter_bpp,
    row_byte_length,
    samples_per_pixel,
    undo_filter,
)


def test_samples_per_pixel_and_row_length():
    assert samples_per_pixel(2) == 3
    assert row_byte_length(8, 8, 2) == 24
    assert filter_bpp(8, 3) == 1
    assert filter_bpp(16, 2) == 6


def test_bitarray_8bit():
    data = bytes([10, 20, 30])
    assert BitArray(data, 8).read_samples(3) == [10, 20, 30]


def test_bitarray_4bit():
    # two 4-bit samples per byte: 0x1a -> 1, 10
    assert BitArray(bytes([0x1A]), 4).read_samples(2) == [1, 10]


def test_bitarray_16bit():
    raw = struct.pack(">HH", 1000, 2000)
    assert BitArray(raw, 16).read_samples(2) == [1000, 2000]


def test_undo_filter_sub():
    header = ImageHeaderParams(4, 1, 8, 0)
    # filtered row where each byte is delta from left
    filtered = bytes([10, 5, 3, 2])
    recon = undo_filter(header, 1, filtered, None)
    assert list(recon) == [10, 15, 18, 20]


def test_apply_filter_roundtrip():
    header = ImageHeaderParams(4, 1, 8, 0)
    original = bytes([10, 15, 18, 20])
    filtered = apply_filter(header, 1, original, None)
    restored = undo_filter(header, 1, filtered, None)
    assert restored == original


def test_image_data_from_rgb_rows():
    header = ImageHeaderParams(2, 2, 8, 2)
    rows = [
        bytes([255, 0, 0, 0, 255, 0]),
        bytes([0, 0, 255, 255, 255, 0]),
    ]
    filtered = bytearray()
    prev = None
    for row in rows:
        filt = apply_filter(header, 0, row, prev)
        filtered.append(0)
        filtered.extend(filt)
        prev = row

    image = ImageData.from_filtered(header, bytes(filtered))
    flat = image.to_flat_pixels()
    assert flat == bytes(rows[0] + rows[1])
    assert image.output_channels == 3
    assert image.output_bit_depth == 8


def test_palette_expansion():
    header = ImageHeaderParams(2, 1, 8, 3)
    palette = [(255, 0, 0), (0, 0, 255)]
    rows = [bytes([0, 1])]
    filtered = b"\x00" + rows[0]
    image = ImageData.from_filtered(header, filtered, palette)
    assert image.to_flat_pixels() == bytes([255, 0, 0, 0, 0, 255])
    assert image.output_channels == 3


def test_grayscale_4bit_scaled():
    header = ImageHeaderParams(4, 1, 4, 0)
    # four 4-bit samples in 2 bytes: 0, 1, 0, 1
    rows = [bytes([0x01, 0x10])]
    filtered = b"\x00" + rows[0]
    image = ImageData.from_filtered(header, filtered)
    flat = image.to_flat_pixels()
    assert flat[0] == 0
    assert flat[1] == 17  # 1 * 255 / 15


def test_interlaced_decode(interlaced_png_path):
    from png_parser import PNGParser

    png = PNGParser().parse(interlaced_png_path)
    flat = png.get_raw_pixels()
    assert len(flat) == 64
    assert list(flat[:8]) == [0, 255, 0, 255, 0, 255, 0, 255]


def test_flat_pixels_roundtrip():
    header = ImageHeaderParams(2, 2, 8, 2)
    rows = [
        bytes([10, 20, 30, 40, 50, 60]),
        bytes([1, 2, 3, 4, 5, 6]),
    ]
    filtered = bytearray()
    prev = None
    for row in rows:
        filtered.append(0)
        filtered.extend(apply_filter(header, 0, row, prev))
        prev = row

    image = ImageData.from_filtered(header, bytes(filtered))
    flat = image.to_flat_pixels()
    restored = ImageData.from_flat_pixels(header, flat)
    assert restored.to_flat_pixels() == flat


def test_to_filtered_bytes():
    header = ImageHeaderParams(2, 1, 8, 0)
    image = ImageData(header=header, rows=[bytes([1, 2])])
    filtered = image.to_filtered_bytes(filter_type=0)
    assert filtered == b"\x00\x01\x02"


def test_palette_image_requires_plte():
    header = ImageHeaderParams(2, 2, 8, 3)
    with pytest.raises(ValueError, match="PLTE"):
        ImageData.from_filtered(header, b"\x00\x00\x01")
