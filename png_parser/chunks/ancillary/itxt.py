"""iTXt – International textual data chunk (UTF-8, optionally compressed)."""

import zlib
from ...chunk import AncillaryChunk


class InternationalTextChunk(AncillaryChunk):
    """
    Stores UTF-8 encoded keyword/value pairs with optional zlib compression.

    Data layout:
        keyword            – 1-79 bytes, null-terminated Latin-1
        compression flag   – 1 byte (0 = uncompressed, 1 = compressed)
        compression method – 1 byte (0 = zlib deflate)
        language tag       – null-terminated ASCII (IETF language tag, may be empty)
        translated keyword – null-terminated UTF-8 (may be empty)
        text               – remaining bytes, UTF-8 (possibly compressed)
    """

    TYPE_CODE: str = "iTXt"

    def decode(self) -> None:
        pos = 0
        data = self.raw_data

        sep = data.index(b"\x00", pos)
        self.keyword: str = data[pos:sep].decode("latin-1")
        pos = sep + 1

        self.compression_flag: int = data[pos]
        pos += 1
        self.compression_method: int = data[pos]
        pos += 1

        sep = data.index(b"\x00", pos)
        self.language_tag: str = data[pos:sep].decode("ascii", errors="replace")
        pos = sep + 1

        sep = data.index(b"\x00", pos)
        self.translated_keyword: str = data[pos:sep].decode("utf-8", errors="replace")
        pos = sep + 1

        raw_text = data[pos:]
        if self.compression_flag == 1:
            raw_text = zlib.decompress(raw_text)
        self.text: str = raw_text.decode("utf-8", errors="replace")

    def display(self) -> str:
        lang = f" [{self.language_tag}]" if self.language_tag else ""
        compressed = " (compressed)" if self.compression_flag else ""
        preview = self.text[:120].replace("\n", "\\n")
        if len(self.text) > 120:
            preview += "…"
        return (
            f"  {self.keyword:<20}{lang}{compressed}\n"
            f"    {preview}"
        )

    def __repr__(self) -> str:
        return (
            f"InternationalTextChunk(keyword={self.keyword!r}, "
            f"lang={self.language_tag!r}, compressed={bool(self.compression_flag)})"
        )
