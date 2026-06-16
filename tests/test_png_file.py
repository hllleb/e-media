"""Tests for PNGFile pixel extraction and serialisation."""

import pytest

from png_parser import PNGParser


def test_get_raw_pixels_rgb(rgb_png_path):
    png = PNGParser().parse(rgb_png_path)
    pixels = png.get_raw_pixels()
    assert len(pixels) == 8 * 8 * 3
    assert pixels[:3] == bytes([255, 0, 0])


def test_get_pixel_layout_palette(palette_png_path):
    png = PNGParser().parse(palette_png_path)
    w, h, c = png.get_pixel_layout()
    assert (w, h, c) == (4, 4, 3)


def test_get_idat_compressed(rgb_png_path):
    png = PNGParser().parse(rgb_png_path)
    compressed = png.get_idat_compressed()
    assert isinstance(compressed, bytes)
    assert len(compressed) > 0


def test_to_bytes_starts_with_signature(rgb_png_path):
    png = PNGParser().parse(rgb_png_path)
    raw = png.to_bytes()
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(raw) > 0


def test_to_bytes_roundtrip(rgb_png_path, tmp_path):
    png = PNGParser().parse(rgb_png_path)
    out = tmp_path / "roundtrip.png"
    png.save(str(out))
    png2 = PNGParser().parse(str(out))
    assert png.get_raw_pixels() == png2.get_raw_pixels()


def test_replace_idat_from_image_data(rgb_png_path, tmp_path):
    png = PNGParser().parse(rgb_png_path)
    image_data = png.get_image_data()
    new_png = png.replace_idat_from_image_data(image_data)
    out = tmp_path / "reencoded.png"
    new_png.save(str(out))
    png2 = PNGParser().parse(str(out))
    assert png.get_raw_pixels() == png2.get_raw_pixels()


def test_replace_idat_from_image_data_rejects_interlaced(interlaced_png_path):
    png = PNGParser().parse(interlaced_png_path)
    image_data = png.get_image_data()
    with pytest.raises(ValueError, match="interlaced"):
        png.replace_idat_from_image_data(image_data)


def test_display_info_contains_offsets(rich_png_path):
    png = PNGParser().parse(rich_png_path)
    report = png.display_info()
    assert "Offset" in report
    assert "gAMA" in report
    assert "WARNING" in report  # trailing bytes
