"""PNGFile – high-level container for a parsed PNG file."""

import zlib

from .signature import PNGSignature
from .chunk import Chunk, CriticalChunk, AncillaryChunk, GenericChunk
from .chunks.critical import (
    IHDRChunk,
    PLTEChunk,
    IDATChunk,
    IENDChunk,
    decompress_idat_chunks,
)
from .image_data import ImageData, ImageHeaderParams


class PNGFile:
    """
    High-level container for a fully parsed PNG file.

    Attributes:
        path           – original file path
        signature      – PNGSignature object
        chunks         – ordered list of all Chunk objects
        chunks_pos     – (start, end) byte offsets per chunk in the source file
        trailing_bytes – any bytes found after IEND (normally empty)
    """

    def __init__(
        self,
        path: str,
        signature: PNGSignature,
        chunks: list[Chunk],
        trailing_bytes: bytes = b"",
        chunks_pos: list[tuple[int, int]] | None = None,
    ) -> None:
        self.path = path
        self.signature = signature
        self.chunks = chunks
        self.trailing_bytes = trailing_bytes
        self.chunks_pos: list[tuple[int, int]] = chunks_pos or []

    # ------------------------------------------------------------------
    # Chunk selectors
    # ------------------------------------------------------------------

    def get_critical_chunks(self) -> list[CriticalChunk]:
        """Return all chunks whose type is critical (uppercase first letter)."""
        return [c for c in self.chunks if isinstance(c, CriticalChunk)]

    def get_ancillary_chunks(self) -> list[AncillaryChunk]:
        """Return all ancillary chunks (lowercase first letter)."""
        return [c for c in self.chunks if isinstance(c, AncillaryChunk)]

    def get_chunks_by_type(self, type_code: str) -> list[Chunk]:
        """Return all chunks matching *type_code* (e.g. ``"tEXt"``)."""
        return [c for c in self.chunks if c.type_code == type_code]

    def get_ihdr(self) -> IHDRChunk:
        """Return the mandatory IHDR chunk (always the first chunk)."""
        for c in self.chunks:
            if isinstance(c, IHDRChunk):
                return c
        raise ValueError("No IHDR chunk found – file may be corrupt.")

    def get_plte(self) -> PLTEChunk | None:
        """Return the PLTE chunk if present."""
        for c in self.chunks:
            if isinstance(c, PLTEChunk):
                return c
        return None

    def get_idat_chunks(self) -> list[IDATChunk]:
        """Return all IDAT chunks in order."""
        return [c for c in self.chunks if isinstance(c, IDATChunk)]

    def get_chunk_offset(self, index: int) -> tuple[int, int] | None:
        """Return inclusive (start, end) file offsets for chunk *index*."""
        if 0 <= index < len(self.chunks_pos):
            return self.chunks_pos[index]
        return None

    # ------------------------------------------------------------------
    # Pixel data extraction (IDAT decompression + filter reconstruction)
    # ------------------------------------------------------------------

    def get_idat_compressed(self) -> bytes:
        """
        Concatenate the compressed payloads of all IDAT chunks.
        This is the raw zlib stream – the entry point for Project 2 encryption.
        """
        return b"".join(c.compressed_data for c in self.get_idat_chunks())

    def get_filtered_idat_bytes(self) -> bytes:
        """Return the decompressed, still-filtered IDAT byte stream."""
        idat_chunks = self.get_idat_chunks()
        if not idat_chunks:
            raise ValueError("No IDAT chunks found.")
        return decompress_idat_chunks(idat_chunks)

    def get_image_data(self, *, expand_palette: bool = True) -> ImageData:
        """
        Decompress IDAT, undo filters (and Adam7 if needed), and return
        an :class:`ImageData` object with full scanlines.
        """
        ihdr = self.get_ihdr()
        header = ImageHeaderParams.from_ihdr(ihdr)
        filtered = self.get_filtered_idat_bytes()
        palette = self.get_plte()
        return ImageData.from_filtered(
            header,
            filtered,
            palette,
            expand_palette=expand_palette,
        )

    def get_raw_pixels(self, *, expand_palette: bool = True) -> bytes:
        """
        Return unfiltered pixel bytes as a flat row-major buffer.

        Supports all color types, bit depths (1-16), palette images, and
        Adam7 interlace.  Indexed colour is expanded to 8-bit RGB by default.
        """
        return self.get_image_data(expand_palette=expand_palette).to_flat_pixels()

    def get_pixel_layout(self, *, expand_palette: bool = True) -> tuple[int, int, int]:
        """
        Return ``(width, height, channels)`` for reshaping flat pixel bytes.
        """
        ihdr = self.get_ihdr()
        image_data = self.get_image_data(expand_palette=expand_palette)
        return (
            ihdr.width,
            ihdr.height,
            image_data.output_channels,
        )

    def replace_idat(self, new_compressed_data: bytes) -> "PNGFile":
        """
        Return a new PNGFile where all IDAT chunks are replaced by a single
        IDAT chunk carrying *new_compressed_data*.

        Project 2 hook: pass encrypted/modified pixel data here.
        """
        new_idat_raw = new_compressed_data
        new_crc = zlib.crc32(b"IDAT" + new_idat_raw) & 0xFFFFFFFF
        new_idat = IDATChunk(len(new_idat_raw), "IDAT", new_idat_raw, new_crc)

        new_chunks: list[Chunk] = []
        idat_inserted = False
        for chunk in self.chunks:
            if isinstance(chunk, IDATChunk):
                if not idat_inserted:
                    new_chunks.append(new_idat)
                    idat_inserted = True
            else:
                new_chunks.append(chunk)

        return PNGFile(
            path=self.path,
            signature=self.signature,
            chunks=new_chunks,
            trailing_bytes=b"",
            chunks_pos=[],
        )

    def replace_idat_from_image_data(
        self,
        image_data: ImageData,
        filter_type: int = 0,
    ) -> "PNGFile":
        """
        Re-filter, compress, and replace IDAT from decoded image rows.

        If the source image used Adam7 interlace, the returned file stores
        scanlines without interlace (IHDR interlace_method set to 0).
        """
        if image_data.header.interlace_method == 1:
            raise ValueError(
                "Re-encoding interlaced images is not supported yet. "
                "Decode with get_image_data() and set interlace_method to 0."
            )

        filtered = image_data.to_filtered_bytes(filter_type)
        compressed = zlib.compress(filtered, level=9)
        return self.replace_idat(compressed)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_bytes(self) -> bytes:
        """
        Reconstruct the full PNG binary from the signature and chunk list.
        No padding or gaps are inserted between chunks.
        Trailing bytes are intentionally NOT included (anonymization benefit).
        """
        parts: list[bytes] = [self.signature.raw]
        for chunk in self.chunks:
            parts.append(chunk.to_bytes())
        return b"".join(parts)

    def save(self, path: str) -> None:
        """Write the reconstructed PNG binary to *path*."""
        with open(path, "wb") as f:
            f.write(self.to_bytes())

    # ------------------------------------------------------------------
    # Display / reporting
    # ------------------------------------------------------------------

    def display_info(self) -> str:
        """
        Return a formatted multi-line string describing the full PNG structure.
        """
        lines: list[str] = []
        sep = "-" * 60

        lines.append(sep)
        lines.append(f"  PNG File: {self.path}")
        lines.append(sep)

        # Signature
        status = "OK" if self.signature.is_valid else "INVALID"
        lines.append(f"\n[Signature] {status}")
        lines.append(f"  Raw bytes: {self.signature.raw!r}")

        # Summary table
        lines.append(f"\n[Chunk summary]  ({len(self.chunks)} chunks total)")
        if self.chunks_pos:
            lines.append(
                f"  {'#':<4} {'Offset':<19} {'Type':<6} {'Length':>8}  "
                f"{'Flags':<30}  {'CRC'}"
            )
            lines.append("  " + "-" * 72)
            for i, chunk in enumerate(self.chunks):
                flags = chunk._flag_summary()
                crc_ok = "OK" if chunk.crc_valid else "FAIL"
                offset = self.get_chunk_offset(i)
                offset_str = (
                    f"{offset[0]:08X}-{offset[1]:08X}" if offset else "n/a"
                )
                lines.append(
                    f"  {i:<4} {offset_str:<19} {chunk.type_code:<6} "
                    f"{chunk.length:>8}  {flags:<30}  {crc_ok}"
                )
        else:
            lines.append(
                f"  {'#':<4} {'Type':<6} {'Length':>8}  {'Flags':<30}  {'CRC'}"
            )
            lines.append("  " + "-" * 56)
            for i, chunk in enumerate(self.chunks):
                flags = chunk._flag_summary()
                crc_ok = "OK" if chunk.crc_valid else "FAIL"
                lines.append(
                    f"  {i:<4} {chunk.type_code:<6} {chunk.length:>8}  "
                    f"{flags:<30}  {crc_ok}"
                )

        # IHDR details
        lines.append(f"\n[IHDR - Image Header]")
        try:
            lines.append(self.get_ihdr().display())
        except ValueError as e:
            lines.append(f"  ERROR: {e}")

        # Critical chunks
        critical = self.get_critical_chunks()
        lines.append(f"\n[Critical chunks]  ({len(critical)} total)")
        for chunk in critical:
            lines.append(f"\n  -- {chunk.type_code} --")
            if hasattr(chunk, "display"):
                lines.append(chunk.display())
            else:
                lines.append(f"  (no display method)")

        # Ancillary chunks
        ancillary = self.get_ancillary_chunks()
        lines.append(f"\n[Ancillary chunks]  ({len(ancillary)} total)")
        if not ancillary:
            lines.append("  (none)")
        for chunk in ancillary:
            lines.append(f"\n  -- {chunk.type_code} --")
            if hasattr(chunk, "display"):
                lines.append(chunk.display())
            else:
                lines.append(repr(chunk))

        # Unknown/generic chunks
        generic = [c for c in self.chunks if isinstance(c, GenericChunk)]
        if generic:
            lines.append(f"\n[Unrecognised chunks]  ({len(generic)} total)")
            for chunk in generic:
                lines.append(f"  {chunk.type_code}: {chunk.length} bytes")

        # Trailing data
        if self.trailing_bytes:
            lines.append(
                f"\n[WARNING] {len(self.trailing_bytes)} trailing bytes found after IEND "
                f"(possible hidden/appended data)."
            )

        # CRC summary
        bad_crcs = [c for c in self.chunks if not c.crc_valid]
        if bad_crcs:
            lines.append(
                f"\n[WARNING] {len(bad_crcs)} chunk(s) with invalid CRC: "
                + ", ".join(c.type_code for c in bad_crcs)
            )

        lines.append(f"\n{sep}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"PNGFile(path={self.path!r}, chunks={len(self.chunks)}, "
            f"trailing={len(self.trailing_bytes)} bytes)"
        )
