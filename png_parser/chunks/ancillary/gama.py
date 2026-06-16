"""gAMA – Image gamma chunk."""

import struct
from ...chunk import AncillaryChunk


class GammaChunk(AncillaryChunk):
    """
    Specifies the relationship between image samples and display output
    intensity.

    Data layout:
        gamma – 4-byte big-endian uint32, equal to gamma * 100 000.

    For example, a stored value of 45455 represents gamma ≈ 0.45455
    (typical for sRGB/Windows images).
    """

    TYPE_CODE: str = "gAMA"

    def decode(self) -> None:
        (self._gamma_raw,) = struct.unpack(">I", self.raw_data)

    @property
    def gamma(self) -> float:
        """Gamma value as a floating-point number."""
        return self._gamma_raw / 100_000.0

    def display(self) -> str:
        return f"  Gamma              : {self.gamma:.5f} (raw={self._gamma_raw})"

    def __repr__(self) -> str:
        return f"GammaChunk(gamma={self.gamma:.5f})"
