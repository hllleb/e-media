"""PNG image data decoding and encoding (filters, interlace, bit depths)."""

from __future__ import annotations

import math
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chunks.critical.ihdr import IHDRChunk
    from .chunks.critical.plte import PLTEChunk

# Adam7 pass geometry: (x_start, y_start, x_step, y_step)
_ADAM7_PASSES = (
    (0, 0, 8, 8),
    (4, 0, 8, 8),
    (0, 4, 4, 8),
    (2, 0, 4, 4),
    (0, 2, 2, 4),
    (1, 0, 2, 2),
    (0, 1, 1, 2),
)


def samples_per_pixel(color_type: int) -> int:
    """Return the number of samples per pixel for a PNG color type."""
    mapping = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    if color_type not in mapping:
        raise ValueError(f"Unsupported color type: {color_type}")
    return mapping[color_type]


def row_byte_length(width: int, bit_depth: int, color_type: int) -> int:
    """Bytes per scanline excluding the filter-type byte."""
    spp = samples_per_pixel(color_type)
    return (width * bit_depth * spp + 7) // 8


def filter_bpp(bit_depth: int, color_type: int) -> int:
    """
    Bytes per pixel used by the PNG filter algorithms.

    For indexed colour and sub-byte depths the filter operates byte-wise
    with bpp = 1, as defined in the PNG specification.
    """
    if color_type == 3 or bit_depth < 8:
        return 1
    return samples_per_pixel(color_type) * (bit_depth // 8)


@dataclass
class ImageHeaderParams:
    """Minimal IHDR fields required for image-data processing."""

    width: int
    height: int
    bit_depth: int
    color_type: int
    interlace_method: int = 0

    @classmethod
    def from_ihdr(cls, ihdr: IHDRChunk) -> ImageHeaderParams:
        return cls(
            ihdr.width,
            ihdr.height,
            ihdr.bit_depth,
            ihdr.color_type,
            ihdr.interlace_method,
        )

    @property
    def uses_palette(self) -> bool:
        return self.color_type == 3


class BitArray(Iterator[int]):
    """Iterate over packed samples with arbitrary bit depth (1, 2, 4, 8, 16)."""

    def __init__(self, data: bytes, bit_depth: int = 8) -> None:
        self._data = data
        self._bit_depth = bit_depth
        self._pos = 0
        self._accumulator = 0
        self._bcount = 0

        if bit_depth == 16:
            self._read_sample = self._read16
        elif bit_depth == 8:
            self._read_sample = self._read8
        elif bit_depth in (1, 2, 4):
            self._read_sample = self._read_subbyte
        else:
            raise ValueError(f"Unsupported bit depth: {bit_depth}")

    def _read8(self) -> int:
        if self._pos >= len(self._data):
            return 0
        value = self._data[self._pos]
        self._pos += 1
        return value

    def _read16(self) -> int:
        if self._pos + 1 >= len(self._data):
            return 0
        value = struct.unpack_from(">H", self._data, self._pos)[0]
        self._pos += 2
        return value

    def _read_subbyte(self) -> int:
        if self._bcount <= 0:
            self._accumulator = self._read8()
            self._bcount = 8
        self._bcount -= self._bit_depth
        mask = (1 << self._bit_depth) - 1
        return (self._accumulator >> self._bcount) & mask

    def __iter__(self) -> BitArray:
        return self

    def __next__(self) -> int:
        if self._pos >= len(self._data) and self._bcount <= 0:
            raise StopIteration
        return self._read_sample()

    def read_samples(self, count: int) -> list[int]:
        """Read exactly *count* samples (padding with zero if the stream ends)."""
        samples: list[int] = []
        for _ in range(count):
            try:
                samples.append(next(self))
            except StopIteration:
                samples.append(0)
        return samples


def _paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def undo_filter(
    header: ImageHeaderParams,
    filter_type: int,
    scanline: bytes,
    previous: bytes | None = None,
) -> bytes:
    """Reverse a PNG scanline filter, returning reconstructed row bytes."""
    result = bytearray(scanline)
    if filter_type == 0:
        return bytes(result)

    bpp = filter_bpp(header.bit_depth, header.color_type)
    prev = previous if previous is not None else bytes(len(scanline))

    if filter_type == 1:  # Sub
        for i in range(bpp, len(result)):
            result[i] = (scanline[i] + result[i - bpp]) & 0xFF
    elif filter_type == 2:  # Up
        for i in range(len(result)):
            result[i] = (scanline[i] + prev[i]) & 0xFF
    elif filter_type == 3:  # Average
        for i in range(len(result)):
            left = result[i - bpp] if i >= bpp else 0
            up = prev[i]
            result[i] = (scanline[i] + ((left + up) >> 1)) & 0xFF
    elif filter_type == 4:  # Paeth
        for i in range(len(result)):
            left = result[i - bpp] if i >= bpp else 0
            up = prev[i]
            corner = prev[i - bpp] if i >= bpp else 0
            result[i] = (scanline[i] + _paeth_predictor(left, up, corner)) & 0xFF
    else:
        raise ValueError(f"Unknown PNG filter type: {filter_type}")

    return bytes(result)


def apply_filter(
    header: ImageHeaderParams,
    filter_type: int,
    scanline: bytes,
    previous: bytes | None = None,
) -> bytes:
    """Apply a PNG scanline filter, returning filtered row bytes."""
    if filter_type == 0:
        return scanline

    bpp = filter_bpp(header.bit_depth, header.color_type)
    prev = previous if previous is not None else bytes(len(scanline))
    result = bytearray(len(scanline))

    if filter_type == 1:  # Sub
        for i, value in enumerate(scanline):
            left = scanline[i - bpp] if i >= bpp else 0
            result[i] = (value - left) & 0xFF
    elif filter_type == 2:  # Up
        for i, value in enumerate(scanline):
            result[i] = (value - prev[i]) & 0xFF
    elif filter_type == 3:  # Average
        for i, value in enumerate(scanline):
            left = scanline[i - bpp] if i >= bpp else 0
            result[i] = (value - ((left + prev[i]) >> 1)) & 0xFF
    elif filter_type == 4:  # Paeth
        for i, value in enumerate(scanline):
            left = scanline[i - bpp] if i >= bpp else 0
            up = prev[i]
            corner = prev[i - bpp] if i >= bpp else 0
            result[i] = (value - _paeth_predictor(left, up, corner)) & 0xFF
    else:
        raise ValueError(f"Unknown PNG filter type: {filter_type}")

    return bytes(result)


def _row_samples(row: bytes, header: ImageHeaderParams) -> list[int]:
    """Extract per-channel samples from one unfiltered scanline."""
    width = header.width
    spp = samples_per_pixel(header.color_type)
    total = width * spp
    return BitArray(row, header.bit_depth).read_samples(total)


def _samples_to_row(samples: list[int], header: ImageHeaderParams) -> bytes:
    """Pack samples back into a PNG scanline byte string."""
    bit_depth = header.bit_depth
    if bit_depth == 16:
        return b"".join(struct.pack(">H", min(s, 0xFFFF)) for s in samples)
    if bit_depth == 8:
        return bytes(min(s, 0xFF) for s in samples)

    # Sub-byte packing (1, 2, 4 bits)
    out = bytearray()
    accumulator = 0
    bits_used = 0
    mask = (1 << bit_depth) - 1
    for sample in samples:
        accumulator = (accumulator << bit_depth) | (sample & mask)
        bits_used += bit_depth
        while bits_used >= 8:
            bits_used -= 8
            out.append((accumulator >> bits_used) & 0xFF)
    if bits_used > 0:
        out.append((accumulator << (8 - bits_used)) & 0xFF)
    return bytes(out)


def _place_pass_row(
    target_row: bytearray,
    pass_row: bytes,
    header: ImageHeaderParams,
    x_start: int,
    x_step: int,
    pixels_in_pass: int,
) -> None:
    """Insert one Adam7 pass row into a full-width image row."""
    spp = samples_per_pixel(header.color_type)
    pass_samples = BitArray(pass_row, header.bit_depth).read_samples(
        pixels_in_pass * spp
    )

    full_samples = _row_samples(bytes(target_row), header)
    sample_index = 0
    for pixel in range(pixels_in_pass):
        x = x_start + pixel * x_step
        if x >= header.width:
            break
        base = x * spp
        for channel in range(spp):
            full_samples[base + channel] = pass_samples[sample_index]
            sample_index += 1

    packed = _samples_to_row(full_samples, header)
    target_row[:] = packed[: len(target_row)]


def _decode_non_interlaced(
    header: ImageHeaderParams, raw: bytes
) -> list[bytes]:
    row_len = row_byte_length(header.width, header.bit_depth, header.color_type)
    rows: list[bytes] = []
    cursor = 0
    previous: bytes | None = None

    for _ in range(header.height):
        if cursor >= len(raw):
            raise ValueError("Truncated PNG image data.")
        filter_type = raw[cursor]
        cursor += 1
        scanline = raw[cursor : cursor + row_len]
        if len(scanline) < row_len:
            raise ValueError("Truncated PNG scanline.")
        cursor += row_len
        reconstructed = undo_filter(header, filter_type, scanline, previous)
        previous = reconstructed
        rows.append(reconstructed)

    return rows


def _decode_interlaced(header: ImageHeaderParams, raw: bytes) -> list[bytes]:
    row_len = row_byte_length(header.width, header.bit_depth, header.color_type)
    image_rows = [bytearray(row_len) for _ in range(header.height)]
    cursor = 0

    for x_start, y_start, x_step, y_step in _ADAM7_PASSES:
        if x_start >= header.width:
            continue

        pixels_per_row = int(math.ceil((header.width - x_start) / x_step))
        pass_row_len = row_byte_length(
            pixels_per_row, header.bit_depth, header.color_type
        )
        previous: bytes | None = None

        for y in range(y_start, header.height, y_step):
            if cursor >= len(raw):
                raise ValueError("Truncated interlaced PNG image data.")
            filter_type = raw[cursor]
            cursor += 1
            scanline = raw[cursor : cursor + pass_row_len]
            if len(scanline) < pass_row_len:
                raise ValueError("Truncated interlaced PNG scanline.")
            cursor += pass_row_len
            reconstructed = undo_filter(header, filter_type, scanline, previous)
            previous = reconstructed
            _place_pass_row(
                image_rows[y],
                reconstructed,
                header,
                x_start,
                x_step,
                pixels_per_row,
            )

    return [bytes(row) for row in image_rows]


@dataclass
class ImageData:
    """
  Decoded PNG pixel rows (unfiltered scanlines).

  Provides conversion to a flat byte buffer suitable for NumPy / FFT and
  re-encoding into a filtered IDAT stream (for Project 2).
  """

    header: ImageHeaderParams
    rows: list[bytes]
    palette: list[tuple[int, int, int]] | None = None
    expand_palette: bool = True

    @classmethod
    def from_filtered(
        cls,
        header: ImageHeaderParams,
        filtered_data: bytes,
        palette: PLTEChunk | list[tuple[int, int, int]] | None = None,
        *,
        expand_palette: bool = True,
    ) -> ImageData:
        palette_entries: list[tuple[int, int, int]] | None
        if palette is None:
            palette_entries = None
        elif hasattr(palette, "entries"):
            palette_entries = palette.entries  # type: ignore[union-attr]
        else:
            palette_entries = palette

        if header.uses_palette and not palette_entries:
            raise ValueError("Indexed-colour image requires a PLTE chunk.")

        if header.interlace_method == 1:
            rows = _decode_interlaced(header, filtered_data)
        elif header.interlace_method == 0:
            rows = _decode_non_interlaced(header, filtered_data)
        else:
            raise ValueError(
                f"Unsupported interlace method: {header.interlace_method}"
            )

        return cls(
            header=header,
            rows=rows,
            palette=palette_entries,
            expand_palette=expand_palette,
        )

    @property
    def output_bit_depth(self) -> int:
        """Bit depth of :meth:`to_flat_pixels` samples."""
        if self.header.uses_palette and self.expand_palette:
            return 8
        if self.header.bit_depth < 8:
            return 8
        return self.header.bit_depth

    @property
    def output_channels(self) -> int:
        """Channel count of :meth:`to_flat_pixels` layout."""
        if self.header.uses_palette and self.expand_palette:
            return 3
        return samples_per_pixel(self.header.color_type)

    def _scale_sample(self, value: int) -> int:
        if self.output_bit_depth == 16:
            max_in = (1 << self.header.bit_depth) - 1
            max_out = 0xFFFF
            return (value * max_out) // max_in if max_in else value
        if self.header.bit_depth < 8:
            max_in = (1 << self.header.bit_depth) - 1
            return (value * 255) // max_in if max_in else value
        return value

    def to_flat_pixels(self) -> bytes:
        """
        Return row-major pixel bytes normalised for analysis.

        Indexed images are expanded to 8-bit RGB when ``expand_palette`` is
        True.  Sub-byte grayscale is scaled to 8 bits.  16-bit samples are
        stored big-endian.
        """
        out = bytearray()
        width = self.header.width
        spp = samples_per_pixel(self.header.color_type)

        for row in self.rows:
            samples = _row_samples(row, self.header)
            for x in range(width):
                if self.header.uses_palette and self.expand_palette:
                    index = samples[x]
                    if self.palette and index < len(self.palette):
                        r, g, b = self.palette[index]
                    else:
                        r = g = b = 0
                    out.extend((r, g, b))
                else:
                    for c in range(spp):
                        value = self._scale_sample(samples[x * spp + c])
                        if self.output_bit_depth == 16:
                            out.extend(struct.pack(">H", value))
                        else:
                            out.append(value)

        return bytes(out)

    def to_filtered_bytes(self, filter_type: int = 0) -> bytes:
        """
        Re-apply scanline filters and return the filtered byte stream
        ready for zlib compression (Project 2 hook).
        """
        out = bytearray()
        previous: bytes | None = None
        for row in self.rows:
            filtered = apply_filter(self.header, filter_type, row, previous)
            out.append(filter_type)
            out.extend(filtered)
            previous = row
        return bytes(out)

    @classmethod
    def from_flat_pixels(
        cls,
        header: ImageHeaderParams,
        flat_pixels: bytes,
        palette: list[tuple[int, int, int]] | None = None,
        *,
        expand_palette: bool = True,
    ) -> ImageData:
        """
        Build scanlines from a flat pixel buffer produced by :meth:`to_flat_pixels`.
        """
        width = header.width
        height = header.height
        out_channels = 3 if header.uses_palette and expand_palette else samples_per_pixel(
            header.color_type
        )
        out_bps = 8 if (header.uses_palette and expand_palette) or header.bit_depth < 8 else header.bit_depth
        sample_size = 2 if out_bps == 16 else 1
        expected = width * height * out_channels * sample_size
        if len(flat_pixels) != expected:
            raise ValueError(
                f"Expected {expected} flat pixel bytes, got {len(flat_pixels)}."
            )

        rows: list[bytes] = []
        cursor = 0
        for _ in range(height):
            row_samples: list[int] = []
            for _x in range(width):
                if header.uses_palette and expand_palette:
                    r = flat_pixels[cursor]
                    g = flat_pixels[cursor + 1]
                    b = flat_pixels[cursor + 2]
                    cursor += 3
                    if palette:
                        try:
                            row_samples.append(palette.index((r, g, b)))
                        except ValueError:
                            row_samples.append(0)
                    else:
                        row_samples.append(r)
                else:
                    for _c in range(out_channels):
                        if out_bps == 16:
                            value = struct.unpack_from(">H", flat_pixels, cursor)[0]
                            cursor += 2
                        else:
                            value = flat_pixels[cursor]
                            cursor += 1
                        if header.bit_depth < 8:
                            max_in = (1 << header.bit_depth) - 1
                            value = (value * max_in) // 255 if max_in else value
                        row_samples.append(value)
            rows.append(_samples_to_row(row_samples, header))

        return cls(
            header=header,
            rows=rows,
            palette=palette,
            expand_palette=expand_palette,
        )
