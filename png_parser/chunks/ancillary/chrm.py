"""cHRM – Primary chromaticities and white point chunk."""

import struct
from ...chunk import AncillaryChunk


class ChromaticitiesChunk(AncillaryChunk):
    """
    Specifies the 1931 CIE x,y chromaticities of the red, green,
    and blue display primaries and the white point used for the image.

    Data layout (32 bytes total, all big-endian uint32 × 100 000):
        white_point_x, white_point_y
        red_x,   red_y
        green_x, green_y
        blue_x,  blue_y
    """

    TYPE_CODE: str = "cHRM"

    def decode(self) -> None:
        values = struct.unpack(">8I", self.raw_data)
        scale = 100_000.0
        (
            self.white_point_x,
            self.white_point_y,
            self.red_x,
            self.red_y,
            self.green_x,
            self.green_y,
            self.blue_x,
            self.blue_y,
        ) = (v / scale for v in values)

    def display(self) -> str:
        return (
            f"  White point        : ({self.white_point_x:.5f}, {self.white_point_y:.5f})\n"
            f"  Red primary        : ({self.red_x:.5f}, {self.red_y:.5f})\n"
            f"  Green primary      : ({self.green_x:.5f}, {self.green_y:.5f})\n"
            f"  Blue primary       : ({self.blue_x:.5f}, {self.blue_y:.5f})"
        )

    def __repr__(self) -> str:
        return (
            f"ChromaticitiesChunk("
            f"wp=({self.white_point_x:.4f},{self.white_point_y:.4f}), "
            f"R=({self.red_x:.4f},{self.red_y:.4f}), "
            f"G=({self.green_x:.4f},{self.green_y:.4f}), "
            f"B=({self.blue_x:.4f},{self.blue_y:.4f}))"
        )
