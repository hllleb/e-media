"""IDAT – Image Data chunk (carries zlib-compressed pixel data)."""

import zlib
from ...chunk import CriticalChunk


class IDATChunk(CriticalChunk):
    """
    Stores a compressed segment of the PNG pixel stream.

    A PNG file may contain multiple consecutive IDAT chunks; they must be
    concatenated before decompression.  This class represents a single IDAT
    chunk.  Decompression and filter-reconstruction are performed at the
    PNGFile level once all IDAT chunks have been collected.

    Project 2 hook:
        ``compressed_data`` is the raw zlib payload – the property that
        Project 2 will encrypt / decrypt.
    """

    TYPE_CODE: str = "IDAT"

    def decode(self) -> None:
        # Keep the raw compressed bytes; no per-chunk decompression here
        # because a valid PNG may split the deflate stream across chunks.
        self.compressed_data: bytes = self.raw_data

    def display(self) -> str:
        return f"  Compressed size    : {len(self.compressed_data)} bytes"

    def __repr__(self) -> str:
        return f"IDATChunk(compressed_size={len(self.compressed_data)})"


def decompress_idat_chunks(idat_chunks: list[IDATChunk]) -> bytes:
    """
    Concatenate the compressed payloads from all IDAT chunks and decompress.

    Returns the raw filtered pixel stream (before PNG filter reconstruction).
    Uses zlib.decompressobj to handle a single deflate stream split across
    multiple IDAT chunks correctly.
    """
    obj = zlib.decompressobj()
    parts: list[bytes] = []
    for chunk in idat_chunks:
        parts.append(obj.decompress(chunk.compressed_data))
    parts.append(obj.flush())
    return b"".join(parts)
