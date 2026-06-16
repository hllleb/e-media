"""Integration test with a real PNG file if present in the repo."""

from pathlib import Path

import pytest

from png_parser import PNGParser

PWR_PNG = Path(__file__).resolve().parent.parent / "pwr.png"


@pytest.mark.skipif(not PWR_PNG.is_file(), reason="pwr.png not in repo")
def test_parse_pwr_png():
    png = PNGParser().parse(str(PWR_PNG))
    ihdr = png.get_ihdr()
    assert ihdr.width > 0
    assert ihdr.height > 0
    assert png.signature.is_valid
    assert len(png.chunks) >= 3
    assert len(png.chunks_pos) == len(png.chunks)


@pytest.mark.skipif(not PWR_PNG.is_file(), reason="pwr.png not in repo")
def test_pwr_pixel_extraction():
    png = PNGParser().parse(str(PWR_PNG))
    w, h, c = png.get_pixel_layout()
    pixels = png.get_raw_pixels()
    bpp = 2 if png.get_image_data().output_bit_depth == 16 else 1
    assert len(pixels) == w * h * c * bpp
