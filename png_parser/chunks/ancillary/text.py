"""tEXt – Textual data chunk (Latin-1 key/value pairs)."""

from ...chunk import AncillaryChunk


class TextChunk(AncillaryChunk):
    """
    Stores a single Latin-1 (ISO-8859-1) keyword/value pair.

    Data layout:
        keyword  – 1-79 bytes, null-terminated Latin-1 string
        text     – remaining bytes (no null terminator)

    Predefined keywords include: Title, Author, Description, Copyright,
    Creation Time, Software, Disclaimer, Warning, Source, Comment.
    """

    TYPE_CODE: str = "tEXt"

    def decode(self) -> None:
        separator = self.raw_data.index(b"\x00")
        self.keyword: str = self.raw_data[:separator].decode("latin-1")
        self.text: str = self.raw_data[separator + 1 :].decode("latin-1")

    def display(self) -> str:
        preview = self.text[:120].replace("\n", "\\n")
        if len(self.text) > 120:
            preview += "…"
        return f"  {self.keyword:<20}: {preview}"

    def __repr__(self) -> str:
        return f"TextChunk(keyword={self.keyword!r}, text_len={len(self.text)})"
