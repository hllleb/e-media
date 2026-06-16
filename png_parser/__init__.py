"""
png_parser – manual OOP PNG parser for the E-Media university project.

Public API::

    from png_parser import PNGParser, PNGAnonymizer, FFTAnalyzer

    png = PNGParser().parse("image.png")
    print(png.display_info())

    anonymizer = PNGAnonymizer()
    stats = anonymizer.save_clean(png, "image_clean.png")
    print(anonymizer.report(stats))

    analyzer = FFTAnalyzer(png)
    analyzer.plot_spectrum()
"""

from .parser import PNGParser
from .png_file import PNGFile
from .anonymizer import PNGAnonymizer
from .fft_analysis import FFTAnalyzer
from .image_data import ImageData, ImageHeaderParams
from .chunk import Chunk, CriticalChunk, AncillaryChunk, GenericChunk
from .signature import PNGSignature

__all__ = [
    "PNGParser",
    "PNGFile",
    "PNGAnonymizer",
    "FFTAnalyzer",
    "ImageData",
    "ImageHeaderParams",
    "Chunk",
    "CriticalChunk",
    "AncillaryChunk",
    "GenericChunk",
    "PNGSignature",
]
