"""eXIf – EXIF metadata chunk (complex ancillary chunk)."""

import struct
from ...chunk import AncillaryChunk

# ---------------------------------------------------------------------------
# EXIF tag name registry (common baseline TIFF/EXIF tags)
# ---------------------------------------------------------------------------
EXIF_TAGS: dict[int, str] = {
    # TIFF baseline tags
    0x010E: "ImageDescription",
    0x010F: "Make",
    0x0110: "Model",
    0x0112: "Orientation",
    0x011A: "XResolution",
    0x011B: "YResolution",
    0x0128: "ResolutionUnit",
    0x0131: "Software",
    0x0132: "DateTime",
    0x013B: "Artist",
    0x013E: "WhitePoint",
    0x013F: "PrimaryChromaticities",
    0x0211: "YCbCrCoefficients",
    0x0213: "YCbCrPositioning",
    0x0214: "ReferenceBlackWhite",
    0x8298: "Copyright",
    # EXIF IFD pointer
    0x8769: "ExifIFD",
    0x8825: "GPSIFD",
    # EXIF IFD tags
    0x9000: "ExifVersion",
    0x9003: "DateTimeOriginal",
    0x9004: "DateTimeDigitized",
    0x9010: "OffsetTime",
    0x9011: "OffsetTimeOriginal",
    0x9101: "ComponentsConfiguration",
    0x9102: "CompressedBitsPerPixel",
    0x9201: "ShutterSpeedValue",
    0x9202: "ApertureValue",
    0x9203: "BrightnessValue",
    0x9204: "ExposureBiasValue",
    0x9205: "MaxApertureValue",
    0x9206: "SubjectDistance",
    0x9207: "MeteringMode",
    0x9208: "LightSource",
    0x9209: "Flash",
    0x920A: "FocalLength",
    0x9214: "SubjectArea",
    0x927C: "MakerNote",
    0x9286: "UserComment",
    0xA000: "FlashpixVersion",
    0xA001: "ColorSpace",
    0xA002: "PixelXDimension",
    0xA003: "PixelYDimension",
    0xA20E: "FocalPlaneXResolution",
    0xA20F: "FocalPlaneYResolution",
    0xA210: "FocalPlaneResolutionUnit",
    0xA217: "SensingMethod",
    0xA300: "FileSource",
    0xA301: "SceneType",
    0xA302: "CFAPattern",
    0xA401: "CustomRendered",
    0xA402: "ExposureMode",
    0xA403: "WhiteBalance",
    0xA404: "DigitalZoomRatio",
    0xA405: "FocalLengthIn35mmFilm",
    0xA406: "SceneCaptureType",
    0xA407: "GainControl",
    0xA408: "Contrast",
    0xA409: "Saturation",
    0xA40A: "Sharpness",
    0xA40C: "SubjectDistanceRange",
    0xA420: "ImageUniqueID",
    # GPS IFD tags
    0x0000: "GPSVersionID",
    0x0001: "GPSLatitudeRef",
    0x0002: "GPSLatitude",
    0x0003: "GPSLongitudeRef",
    0x0004: "GPSLongitude",
    0x0005: "GPSAltitudeRef",
    0x0006: "GPSAltitude",
    0x0007: "GPSTimeStamp",
    0x0012: "GPSMapDatum",
    0x001D: "GPSDateStamp",
}

# TIFF type code → (struct format char, byte size)
_TIFF_TYPES: dict[int, tuple[str, int]] = {
    1: ("B", 1),   # BYTE
    2: ("s", 1),   # ASCII
    3: ("H", 2),   # SHORT
    4: ("I", 4),   # LONG
    5: ("II", 8),  # RATIONAL (two LONGs: numerator, denominator)
    6: ("b", 1),   # SBYTE
    7: ("B", 1),   # UNDEFINED
    8: ("h", 2),   # SSHORT
    9: ("i", 4),   # SLONG
    10: ("ii", 8), # SRATIONAL
    11: ("f", 4),  # FLOAT
    12: ("d", 8),  # DOUBLE
}


class ExifChunk(AncillaryChunk):
    """
    Decodes the eXIf chunk which embeds raw Exif (TIFF-structured) metadata.

    The chunk data is a raw Exif payload – identical to what you would find
    in a JPEG APP1 marker after the "Exif\\x00\\x00" prefix.

    Parsing strategy:
        1. Detect byte order from the TIFF header ("II" = little-endian,
           "MM" = big-endian).
        2. Walk the first Image File Directory (IFD0).
        3. Follow the ExifIFD and GPSIFD sub-directory pointers if present.
        4. Decode each tag value according to its TIFF type code.
    """

    TYPE_CODE: str = "eXIf"

    def decode(self) -> None:
        self.tags: dict[str, object] = {}
        self.raw_tags: dict[int, object] = {}
        self._parse_errors: list[str] = []

        if len(self.raw_data) < 8:
            self._parse_errors.append("Payload too short to be valid EXIF.")
            return

        # Detect byte order
        bom = self.raw_data[:2]
        if bom == b"II":
            self._endian = "<"  # little-endian
        elif bom == b"MM":
            self._endian = ">"  # big-endian
        else:
            self._parse_errors.append(f"Unknown byte order marker: {bom!r}")
            return

        # Validate TIFF magic (42)
        magic = struct.unpack_from(f"{self._endian}H", self.raw_data, 2)[0]
        if magic != 42:
            self._parse_errors.append(
                f"TIFF magic number mismatch: expected 42, got {magic}."
            )
            return

        ifd0_offset = struct.unpack_from(f"{self._endian}I", self.raw_data, 4)[0]
        self._parse_ifd(ifd0_offset, follow_sub_ifds=True)

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    def _parse_ifd(self, offset: int, follow_sub_ifds: bool = False) -> None:
        """Parse an IFD starting at *offset* within self.raw_data."""
        data = self.raw_data
        endian = self._endian

        if offset + 2 > len(data):
            return

        num_entries = struct.unpack_from(f"{endian}H", data, offset)[0]
        pos = offset + 2

        sub_ifd_offsets: list[int] = []

        for _ in range(num_entries):
            if pos + 12 > len(data):
                break

            tag_id, type_code, count = struct.unpack_from(
                f"{endian}HHI", data, pos
            )
            value_or_offset_raw = data[pos + 8 : pos + 12]
            pos += 12

            tag_name = EXIF_TAGS.get(tag_id, f"Tag_0x{tag_id:04X}")
            value = self._decode_value(
                type_code, count, value_or_offset_raw
            )

            self.raw_tags[tag_id] = value
            self.tags[tag_name] = value

            # Collect sub-IFD pointers for later traversal
            if follow_sub_ifds and tag_id in (0x8769, 0x8825):
                sub_offset = struct.unpack_from(f"{endian}I", value_or_offset_raw)[0]
                sub_ifd_offsets.append(sub_offset)

        for sub_offset in sub_ifd_offsets:
            self._parse_ifd(sub_offset, follow_sub_ifds=False)

    def _decode_value(
        self, type_code: int, count: int, value_or_offset_raw: bytes
    ) -> object:
        """
        Decode a tag value from either the inline 4-byte field or from
        the offset it points to in the data block.
        """
        data = self.raw_data
        endian = self._endian

        if type_code not in _TIFF_TYPES:
            return value_or_offset_raw  # return raw bytes for unknown types

        fmt_char, byte_size = _TIFF_TYPES[type_code]
        total_bytes = byte_size * count

        if total_bytes <= 4:
            raw = value_or_offset_raw[:total_bytes]
        else:
            offset = struct.unpack_from(f"{endian}I", value_or_offset_raw)[0]
            if offset + total_bytes > len(data):
                return None
            raw = data[offset : offset + total_bytes]

        # ASCII type: decode as string
        if type_code == 2:
            return raw.rstrip(b"\x00").decode("ascii", errors="replace")

        # UNDEFINED type: return raw bytes
        if type_code == 7:
            return raw

        # RATIONAL / SRATIONAL: list of (numerator, denominator) tuples
        if type_code in (5, 10):
            sub_fmt = f"{endian}{fmt_char}"
            sub_size = byte_size // 2
            pairs = []
            for i in range(count):
                n = struct.unpack_from(sub_fmt[0] + fmt_char[0], raw, i * byte_size)[0]
                d = struct.unpack_from(sub_fmt[0] + fmt_char[0], raw, i * byte_size + sub_size)[0]
                pairs.append((n, d))
            return pairs[0] if count == 1 else pairs

        # Numeric types
        full_fmt = f"{endian}{count}{fmt_char}"
        try:
            values = struct.unpack(full_fmt, raw)
        except struct.error:
            return raw
        return values[0] if count == 1 else list(values)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display(self) -> str:
        if not self.tags and self._parse_errors:
            return "  EXIF parse errors: " + "; ".join(self._parse_errors)

        lines = [f"  EXIF tags ({len(self.tags)} entries):"]
        for name, value in self.tags.items():
            if isinstance(value, bytes) and len(value) > 32:
                display_val = f"<{len(value)} bytes>"
            else:
                display_val = str(value)[:80]
            lines.append(f"    {name:<35}: {display_val}")

        if self._parse_errors:
            lines.append("  Warnings: " + "; ".join(self._parse_errors))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ExifChunk(tags={len(self.tags)}, errors={len(self._parse_errors)})"
