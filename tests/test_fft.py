"""Tests for FFTAnalyzer."""

import numpy as np

from png_parser import FFTAnalyzer, PNGParser


def test_compute_fft_shape(rgb_png_path):
    png = PNGParser().parse(rgb_png_path)
    analyzer = FFTAnalyzer(png)
    spectrum = analyzer.compute_fft()
    ihdr = png.get_ihdr()
    assert spectrum.shape == (ihdr.height, ihdr.width)


def test_pixel_array_normalized(rgb_png_path):
    png = PNGParser().parse(rgb_png_path)
    pixels = FFTAnalyzer(png).get_pixel_array()
    assert pixels.dtype == np.float64
    assert pixels.shape == (8, 8)
    assert pixels.min() >= 0.0
    assert pixels.max() <= 1.0


def test_verify_with_synthetic_passes():
    assert FFTAnalyzer.verify_with_synthetic(frequency=8, show=False) is True


def test_fft_on_palette_image(palette_png_path):
    png = PNGParser().parse(palette_png_path)
    analyzer = FFTAnalyzer(png)
    spectrum = analyzer.compute_fft()
    assert spectrum.shape == (4, 4)
