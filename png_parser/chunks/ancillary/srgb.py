"""sRGB – Standard RGB colour space chunk."""

import struct
from ...chunk import AncillaryChunk

RENDERING_INTENTS: dict[int, str] = {
    0: "Perceptual",
    1: "Relative colorimetric",
    2: "Saturation",
    3: "Absolute colorimetric",
}


class StandardRGBChunk(AncillaryChunk):
    """
    Indicates that the image samples are in the sRGB colour space
    and specifies the rendering intent.

    Data layout:
        rendering_intent – 1 byte
    """

    TYPE_CODE: str = "sRGB"

    def decode(self) -> None:
        (self.rendering_intent,) = struct.unpack("B", self.raw_data)

    @property
    def rendering_intent_name(self) -> str:
        return RENDERING_INTENTS.get(
            self.rendering_intent, f"Unknown ({self.rendering_intent})"
        )

    def display(self) -> str:
        return (
            f"  Rendering intent   : {self.rendering_intent} - "
            f"{self.rendering_intent_name}"
        )

    def __repr__(self) -> str:
        return f"StandardRGBChunk(intent={self.rendering_intent_name!r})"
