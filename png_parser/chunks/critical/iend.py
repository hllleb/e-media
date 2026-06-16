"""IEND – Image End chunk (marks the end of the PNG datastream)."""

from ...chunk import CriticalChunk


class IENDChunk(CriticalChunk):
    """
    The IEND chunk has zero data bytes.
    Its presence signals that all image data has been read.
    Any bytes found after IEND in the file are outside the PNG stream
    and may represent hidden/appended data.
    """

    TYPE_CODE: str = "IEND"

    def decode(self) -> None:
        if len(self.raw_data) != 0:
            raise ValueError(
                f"IEND chunk must have zero data bytes, "
                f"got {len(self.raw_data)}."
            )

    def display(self) -> str:
        return "  (no data - end of PNG stream)"

    def __repr__(self) -> str:
        return "IENDChunk()"
