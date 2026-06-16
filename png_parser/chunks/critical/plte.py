"""PLTE – Palette chunk (required for indexed-color, optional for RGB/RGBA)."""

import struct
from ...chunk import CriticalChunk


class PLTEChunk(CriticalChunk):
    """
    Decodes the PLTE chunk which holds a palette of up to 256 RGB entries.

    The data length must be divisible by 3 (each entry is R, G, B).
    Palette entries are indexed 0..N-1 and referenced by IDAT data
    when the image color type is 3 (Indexed-color).
    """

    TYPE_CODE: str = "PLTE"

    def decode(self) -> None:
        if len(self.raw_data) % 3 != 0:
            raise ValueError(
                f"PLTE data length must be a multiple of 3, "
                f"got {len(self.raw_data)}."
            )
        n = len(self.raw_data) // 3
        self.entries: list[tuple[int, int, int]] = [
            struct.unpack_from("BBB", self.raw_data, i * 3) for i in range(n)
        ]

    @property
    def num_entries(self) -> int:
        return len(self.entries)

    def display(self) -> str:
        lines = [f"  Palette entries    : {self.num_entries}"]
        # Show first 8 entries to keep output manageable
        for i, (r, g, b) in enumerate(self.entries[:8]):
            lines.append(f"  [{i:3d}] R={r:3d} G={g:3d} B={b:3d}")
        if self.num_entries > 8:
            lines.append(f"  ... ({self.num_entries - 8} more entries)")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"PLTEChunk(entries={self.num_entries})"
