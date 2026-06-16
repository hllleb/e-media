"""Base Chunk class and abstract subclasses for critical / ancillary chunks."""

import struct
import zlib
from abc import ABC, abstractmethod


class Chunk:
    """
    Represents a single raw PNG chunk as read from the file.

    PNG chunk layout (per spec):
        4 bytes  – data length  (big-endian uint32, does NOT include type or CRC)
        4 bytes  – type code    (4 ASCII letters, case encodes metadata)
        N bytes  – data
        4 bytes  – CRC32        (covers type + data)

    Chunk-type byte flags (bit 5 of each byte, 0-indexed):
        Byte 0 bit 5 = 0  →  critical chunk   (uppercase first letter)
        Byte 0 bit 5 = 1  →  ancillary chunk  (lowercase first letter)
        Byte 1 bit 5 = 0  →  public chunk     (uppercase second letter)
        Byte 1 bit 5 = 1  →  private chunk    (lowercase second letter)
        Byte 2 bit 5 = 0  →  reserved (must be 0 in conformant files)
        Byte 3 bit 5 = 0  →  unsafe to copy if image is modified
        Byte 3 bit 5 = 1  →  safe to copy
    """

    def __init__(
        self,
        length: int,
        type_code: str,
        raw_data: bytes,
        crc: int,
    ) -> None:
        self.length: int = length
        self.type_code: str = type_code  # e.g. "IHDR", "tEXt", "eXIf"
        self.raw_data: bytes = raw_data
        self.crc: int = crc

    # ------------------------------------------------------------------
    # Chunk-type flag properties (derived from the ASCII letters)
    # ------------------------------------------------------------------

    @property
    def is_ancillary(self) -> bool:
        """True when the first letter is lowercase (bit 5 of byte 0 is 1)."""
        return bool(ord(self.type_code[0]) & 0x20)

    @property
    def is_critical(self) -> bool:
        """True when the first letter is uppercase (bit 5 of byte 0 is 0)."""
        return not self.is_ancillary

    @property
    def is_private(self) -> bool:
        """True when the second letter is lowercase."""
        return bool(ord(self.type_code[1]) & 0x20)

    @property
    def is_public(self) -> bool:
        """True when the second letter is uppercase."""
        return not self.is_private

    @property
    def is_reserved_bit_valid(self) -> bool:
        """True when the third letter is uppercase (reserved bit must be 0)."""
        return not bool(ord(self.type_code[2]) & 0x20)

    @property
    def is_safe_to_copy(self) -> bool:
        """True when the fourth letter is lowercase."""
        return bool(ord(self.type_code[3]) & 0x20)

    # ------------------------------------------------------------------
    # CRC validation
    # ------------------------------------------------------------------

    @property
    def computed_crc(self) -> int:
        """Compute CRC32 over (type bytes + data), as per the PNG spec."""
        return zlib.crc32(self.type_code.encode("ascii") + self.raw_data) & 0xFFFFFFFF

    @property
    def crc_valid(self) -> bool:
        """True if the stored CRC matches the computed CRC."""
        return self.crc == self.computed_crc

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_bytes(self) -> bytes:
        """
        Reconstruct the chunk's on-disk binary representation.
        Uses the *stored* CRC to preserve the original file exactly.
        """
        return (
            struct.pack(">I", self.length)
            + self.type_code.encode("ascii")
            + self.raw_data
            + struct.pack(">I", self.crc)
        )

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _flag_summary(self) -> str:
        flags = []
        flags.append("critical" if self.is_critical else "ancillary")
        flags.append("public" if self.is_public else "private")
        if self.is_safe_to_copy:
            flags.append("safe-to-copy")
        if not self.crc_valid:
            flags.append("CRC-MISMATCH")
        return ", ".join(flags)

    def __repr__(self) -> str:
        return (
            f"Chunk(type={self.type_code!r}, length={self.length}, "
            f"flags=[{self._flag_summary()}], crc_valid={self.crc_valid})"
        )


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------


class CriticalChunk(Chunk, ABC):
    """
    Base class for the four mandatory PNG chunk types:
    IHDR, PLTE, IDAT, IEND.

    Subclasses must implement ``decode()`` which populates their
    type-specific attributes from ``self.raw_data``.
    """

    def __init__(
        self,
        length: int,
        type_code: str,
        raw_data: bytes,
        crc: int,
    ) -> None:
        super().__init__(length, type_code, raw_data, crc)
        self.decode()

    @abstractmethod
    def decode(self) -> None:
        """Parse ``self.raw_data`` and populate typed attributes."""


class AncillaryChunk(Chunk, ABC):
    """
    Base class for optional PNG chunk types (tEXt, pHYs, tIME, …).

    Subclasses must implement ``decode()`` which populates their
    type-specific attributes from ``self.raw_data``.
    """

    def __init__(
        self,
        length: int,
        type_code: str,
        raw_data: bytes,
        crc: int,
    ) -> None:
        super().__init__(length, type_code, raw_data, crc)
        self.decode()

    @abstractmethod
    def decode(self) -> None:
        """Parse ``self.raw_data`` and populate typed attributes."""


class GenericChunk(Chunk):
    """
    Fallback for chunk types that have no dedicated decoder.
    The raw data is preserved as-is so the file can still be
    reconstructed faithfully.
    """

    def __repr__(self) -> str:
        return (
            f"GenericChunk(type={self.type_code!r}, length={self.length}, "
            f"flags=[{self._flag_summary()}])"
        )
