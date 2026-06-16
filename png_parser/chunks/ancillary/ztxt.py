"""zTXt – Compressed textual data chunk."""

import zlib
from ...chunk import AncillaryChunk


class CompressedTextChunk(AncillaryChunk):
    """
    Like tEXt but the value is zlib-compressed.

    Data layout:
        keyword            – 1-79 bytes, null-terminated Latin-1
        compression method – 1 byte (always 0 = deflate)
        compressed text    – remaining bytes
    """

    TYPE_CODE: str = "zTXt"

    def decode(self) -> None:
        sep = self.raw_data.index(b"\x00")
        self.keyword: str = self.raw_data[:sep].decode("latin-1")
        pos = sep + 1
        self.compression_method: int = self.raw_data[pos]
        pos += 1
        self.text: str = zlib.decompress(self.raw_data[pos:]).decode(
            "latin-1", errors="replace"
        )

    def display(self) -> str:
        preview = self.text[:120].replace("\n", "\\n")
        if len(self.text) > 120:
            preview += "…"
        return f"  {self.keyword:<20} (zlib): {preview}"

    def __repr__(self) -> str:
        return (
            f"CompressedTextChunk(keyword={self.keyword!r}, "
            f"text_len={len(self.text)})"
        )
