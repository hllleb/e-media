"""pHYs – Physical pixel dimensions chunk."""

import struct
from ...chunk import AncillaryChunk

UNIT_NAMES: dict[int, str] = {
    0: "unknown",
    1: "metre",
}


class PhysicalPixelDimensionsChunk(AncillaryChunk):
    """
    Specifies the intended pixel size or aspect ratio.

    Data layout:
        pixels_per_unit_x – 4-byte big-endian uint32
        pixels_per_unit_y – 4-byte big-endian uint32
        unit              – 1 byte (0 = unknown/aspect ratio, 1 = metre)
    """

    TYPE_CODE: str = "pHYs"

    def decode(self) -> None:
        self.pixels_per_unit_x, self.pixels_per_unit_y, self.unit = struct.unpack(
            ">IIB", self.raw_data
        )

    @property
    def unit_name(self) -> str:
        return UNIT_NAMES.get(self.unit, f"unknown unit ({self.unit})")

    @property
    def dpi_x(self) -> float | None:
        """Dots per inch in X, only meaningful when unit == 1 (metre)."""
        if self.unit == 1:
            return self.pixels_per_unit_x / 39.3701
        return None

    @property
    def dpi_y(self) -> float | None:
        if self.unit == 1:
            return self.pixels_per_unit_y / 39.3701
        return None

    def display(self) -> str:
        lines = [
            f"  Pixels per unit X  : {self.pixels_per_unit_x}",
            f"  Pixels per unit Y  : {self.pixels_per_unit_y}",
            f"  Unit               : {self.unit} - {self.unit_name}",
        ]
        if self.dpi_x is not None:
            lines.append(f"  DPI (X / Y)        : {self.dpi_x:.1f} / {self.dpi_y:.1f}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"PhysicalPixelDimensionsChunk("
            f"x={self.pixels_per_unit_x}, y={self.pixels_per_unit_y}, "
            f"unit={self.unit_name!r})"
        )
