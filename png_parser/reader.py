"""Low-level binary reader for PNG files."""

import struct


class PNGReader:
    """
    Reads raw bytes from a PNG file sequentially.
    Maintains an internal position pointer so callers can
    consume the stream chunk by chunk without manual offset tracking.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        with open(path, "rb") as f:
            self.data: bytes = f.read()
        self.pos: int = 0

    # ------------------------------------------------------------------
    # Core read primitives
    # ------------------------------------------------------------------

    def read(self, n: int) -> bytes:
        """Consume and return the next *n* bytes, advancing the position."""
        if self.pos + n > len(self.data):
            raise EOFError(
                f"Attempted to read {n} bytes at offset {self.pos} "
                f"but only {len(self.data) - self.pos} bytes remain."
            )
        chunk = self.data[self.pos : self.pos + n]
        self.pos += n
        return chunk

    def read_uint32(self) -> int:
        """Read a 4-byte big-endian unsigned integer."""
        return struct.unpack(">I", self.read(4))[0]

    def peek(self, n: int) -> bytes:
        """Return the next *n* bytes without advancing the position."""
        return self.data[self.pos : self.pos + n]

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def remaining(self) -> int:
        """Number of bytes left in the stream."""
        return len(self.data) - self.pos

    @property
    def at_end(self) -> bool:
        """True when all bytes have been consumed."""
        return self.pos >= len(self.data)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"PNGReader(path={self.path!r}, "
            f"pos={self.pos}/{len(self.data)})"
        )
