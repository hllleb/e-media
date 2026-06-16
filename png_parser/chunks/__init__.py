"""
Chunk factory: maps 4-character PNG chunk type codes to their decoder classes.

Usage::

    chunk = chunk_factory("IHDR", length=13, raw_data=b"...", crc=0xDEADBEEF)
    # returns an IHDRChunk instance

Unknown chunk types fall back to GenericChunk so the file can still be
reconstructed without data loss.
"""

from ..chunk import Chunk, GenericChunk
from .critical import IHDRChunk, PLTEChunk, IDATChunk, IENDChunk
from .ancillary import (
    TextChunk,
    InternationalTextChunk,
    CompressedTextChunk,
    GammaChunk,
    PhysicalPixelDimensionsChunk,
    TimeChunk,
    StandardRGBChunk,
    ChromaticitiesChunk,
    ExifChunk,
)

# ---------------------------------------------------------------------------
# Registry: type code → class
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, type[Chunk]] = {
    # Critical chunks
    "IHDR": IHDRChunk,
    "PLTE": PLTEChunk,
    "IDAT": IDATChunk,
    "IEND": IENDChunk,
    # Ancillary chunks
    "tEXt": TextChunk,
    "iTXt": InternationalTextChunk,
    "zTXt": CompressedTextChunk,
    "gAMA": GammaChunk,
    "pHYs": PhysicalPixelDimensionsChunk,
    "tIME": TimeChunk,
    "sRGB": StandardRGBChunk,
    "cHRM": ChromaticitiesChunk,
    "eXIf": ExifChunk,
}


def chunk_factory(
    type_code: str,
    length: int,
    raw_data: bytes,
    crc: int,
) -> Chunk:
    """
    Instantiate the most specific Chunk subclass for the given *type_code*.

    If no dedicated class is registered, returns a :class:`GenericChunk`
    that stores the raw bytes without decoding them.  This ensures the
    parser never crashes on unknown chunk types and the file can always
    be reconstructed faithfully.
    """
    cls = _REGISTRY.get(type_code, GenericChunk)
    return cls(length, type_code, raw_data, crc)


def registered_types() -> list[str]:
    """Return a sorted list of all registered chunk type codes."""
    return sorted(_REGISTRY.keys())


__all__ = [
    "chunk_factory",
    "registered_types",
    # Re-export all chunk classes for convenience
    "IHDRChunk",
    "PLTEChunk",
    "IDATChunk",
    "IENDChunk",
    "TextChunk",
    "InternationalTextChunk",
    "CompressedTextChunk",
    "GammaChunk",
    "PhysicalPixelDimensionsChunk",
    "TimeChunk",
    "StandardRGBChunk",
    "ChromaticitiesChunk",
    "ExifChunk",
    "GenericChunk",
]
