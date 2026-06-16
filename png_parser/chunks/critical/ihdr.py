"""IHDR – Image Header chunk (must be the first chunk in every PNG)."""

import struct
from ...chunk import CriticalChunk

# PNG color type constants
COLOR_TYPES: dict[int, str] = {
    0: "Grayscale",
    2: "RGB (Truecolor)",
    3: "Indexed-color (Palette)",
    4: "Grayscale + Alpha",
    6: "RGBA (Truecolor + Alpha)",
}

# Allowed bit-depths per color type
ALLOWED_BIT_DEPTHS: dict[int, list[int]] = {
    0: [1, 2, 4, 8, 16],
    2: [8, 16],
    3: [1, 2, 4, 8],
    4: [8, 16],
    6: [8, 16],
}

INTERLACE_METHODS: dict[int, str] = {
    0: "No interlace",
    1: "Adam7 interlace",
}


class IHDRChunk(CriticalChunk):
    """
    Decodes the 13-byte IHDR data field.

    Fields (all integers, big-endian where applicable):
        width             – 4 bytes, image width in pixels
        height            – 4 bytes, image height in pixels
        bit_depth         – 1 byte,  bits per channel sample
        color_type        – 1 byte,  color interpretation code
        compression_method– 1 byte,  always 0 (deflate/inflate)
        filter_method     – 1 byte,  always 0 (adaptive filtering)
        interlace_method  – 1 byte,  0 = no interlace, 1 = Adam7
    """

    TYPE_CODE: str = "IHDR"
    DATA_LENGTH: int = 13

    def decode(self) -> None:
        if len(self.raw_data) != self.DATA_LENGTH:
            raise ValueError(
                f"IHDR data must be {self.DATA_LENGTH} bytes, "
                f"got {len(self.raw_data)}."
            )
        (
            self.width,
            self.height,
            self.bit_depth,
            self.color_type,
            self.compression_method,
            self.filter_method,
            self.interlace_method,
        ) = struct.unpack(">IIBBBBB", self.raw_data)

    # ------------------------------------------------------------------
    # Human-readable interpretations
    # ------------------------------------------------------------------

    @property
    def color_type_name(self) -> str:
        return COLOR_TYPES.get(self.color_type, f"Unknown ({self.color_type})")

    @property
    def interlace_name(self) -> str:
        return INTERLACE_METHODS.get(
            self.interlace_method, f"Unknown ({self.interlace_method})"
        )

    @property
    def channels(self) -> int:
        """Number of color channels implied by the color type."""
        return {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(self.color_type, 0)

    @property
    def bytes_per_pixel(self) -> int:
        """Bytes consumed per pixel (rounded up to full bytes)."""
        return max(1, (self.bit_depth * self.channels + 7) // 8)

    def display(self) -> str:
        lines = [
            f"  Width              : {self.width} px",
            f"  Height             : {self.height} px",
            f"  Bit depth          : {self.bit_depth} bits/channel",
            f"  Color type         : {self.color_type} - {self.color_type_name}",
            f"  Channels           : {self.channels}",
            f"  Bytes per pixel    : {self.bytes_per_pixel}",
            f"  Compression method : {self.compression_method} (deflate/inflate)",
            f"  Filter method      : {self.filter_method} (adaptive)",
            f"  Interlace method   : {self.interlace_method} - {self.interlace_name}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"IHDRChunk({self.width}x{self.height}, "
            f"bit_depth={self.bit_depth}, color_type={self.color_type_name!r})"
        )
