"""tIME – Image last-modification time chunk."""

import struct
from datetime import datetime, timezone
from ...chunk import AncillaryChunk


class TimeChunk(AncillaryChunk):
    """
    Records the last time the image was modified.

    Data layout (7 bytes total):
        year   – 2-byte big-endian uint16 (full year, e.g. 2024)
        month  – 1 byte (1–12)
        day    – 1 byte (1–31)
        hour   – 1 byte (0–23)
        minute – 1 byte (0–59)
        second – 1 byte (0–60, 60 for leap seconds)
    """

    TYPE_CODE: str = "tIME"

    def decode(self) -> None:
        self.year, self.month, self.day, self.hour, self.minute, self.second = (
            struct.unpack(">HBBBBB", self.raw_data)
        )

    @property
    def as_datetime(self) -> datetime:
        """Return a timezone-aware UTC datetime object."""
        return datetime(
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            min(self.second, 59),  # datetime doesn't support leap seconds
            tzinfo=timezone.utc,
        )

    def display(self) -> str:
        return (
            f"  Last modified      : "
            f"{self.year:04d}-{self.month:02d}-{self.day:02d} "
            f"{self.hour:02d}:{self.minute:02d}:{self.second:02d} UTC"
        )

    def __repr__(self) -> str:
        return f"TimeChunk({self.as_datetime.isoformat()})"
