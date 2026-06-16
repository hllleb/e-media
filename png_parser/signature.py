"""PNG signature validation."""

from .reader import PNGReader

# The 8-byte magic number defined in the PNG specification.
PNG_SIGNATURE: bytes = b"\x89PNG\r\n\x1a\n"


class PNGSignature:
    """
    Represents and validates the 8-byte PNG file signature.

    The bytes encode several intentional properties (from the PNG spec):
      - 0x89           : non-ASCII byte – catches 7-bit transport corruption
      - PNG            : human-readable identification
      - \\r\\n (0x0D 0x0A): DOS line-ending check
      - 0x1A           : stops display under DOS `type` command
      - \\n  (0x0A)     : Unix line-ending check
    """

    LENGTH: int = 8

    def __init__(self, raw: bytes) -> None:
        if len(raw) != self.LENGTH:
            raise ValueError(
                f"PNG signature must be exactly {self.LENGTH} bytes, "
                f"got {len(raw)}."
            )
        self.raw: bytes = raw

    @classmethod
    def from_reader(cls, reader: PNGReader) -> "PNGSignature":
        """Read 8 bytes from *reader* and construct a PNGSignature."""
        return cls(reader.read(cls.LENGTH))

    @property
    def is_valid(self) -> bool:
        """Return True if the raw bytes match the PNG magic number."""
        return self.raw == PNG_SIGNATURE

    def validate(self) -> None:
        """Raise ValueError if the signature does not match."""
        if not self.is_valid:
            raise ValueError(
                f"Invalid PNG signature: {self.raw!r}. "
                f"Expected: {PNG_SIGNATURE!r}"
            )

    def __repr__(self) -> str:  # pragma: no cover
        status = "valid" if self.is_valid else "INVALID"
        return f"PNGSignature({self.raw!r}, {status})"
