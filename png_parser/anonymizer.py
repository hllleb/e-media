"""PNGAnonymizer – strips ancillary chunks and hidden data from a PNG file."""

import os
import zlib
from .chunk import CriticalChunk, AncillaryChunk
from .png_file import PNGFile


class PNGAnonymizer:
    """
    Removes metadata from a PNG file without altering the image content.

    Two kinds of "extra" data are removed:

    1. **Ancillary chunks** – tEXt, iTXt, eXIf, gAMA, pHYs, tIME, sRGB, …
       These carry non-image metadata (author, GPS, copyright, colour profile,
       etc.) that can identify the creator or device.

    2. **Trailing bytes** – bytes that appear after the IEND chunk.
       Some tools append hidden data here; reconstruction from the parsed
       chunk list naturally omits them.

    The output file is a minimal, standard-conformant PNG whose visual
    content is identical to the original.
    """

    def strip_ancillary(self, png_file: PNGFile) -> PNGFile:
        """
        Return a new :class:`PNGFile` that contains only the critical chunks
        from *png_file* (IHDR, PLTE if present, all IDAT, IEND).

        The original PNGFile is not modified.
        """
        critical_only = [c for c in png_file.chunks if isinstance(c, CriticalChunk)]

        return PNGFile(
            path=png_file.path,
            signature=png_file.signature,
            chunks=critical_only,
            trailing_bytes=b"",  # explicitly drop trailing data
        )

    def save_clean(self, png_file: PNGFile, output_path: str) -> dict:
        """
        Strip ancillary chunks from *png_file* and write the result to
        *output_path*.

        Returns a summary dict with statistics about what was removed.
        """
        original_chunks = png_file.chunks
        ancillary = [c for c in original_chunks if isinstance(c, AncillaryChunk)]
        trailing_size = len(png_file.trailing_bytes)

        cleaned = self.strip_ancillary(png_file)
        cleaned.save(output_path)

        original_size = os.path.getsize(png_file.path) if os.path.isfile(png_file.path) else None
        new_size = os.path.getsize(output_path)

        return {
            "output_path": output_path,
            "original_chunks": len(original_chunks),
            "removed_chunks": len(ancillary),
            "removed_chunk_types": [c.type_code for c in ancillary],
            "trailing_bytes_removed": trailing_size,
            "original_size_bytes": original_size,
            "new_size_bytes": new_size,
            "bytes_saved": (original_size - new_size) if original_size else None,
        }

    def report(self, stats: dict) -> str:
        """Format the summary dict returned by :meth:`save_clean` as text."""
        lines = [
            "Anonymization complete",
            f"  Output             : {stats['output_path']}",
            f"  Original size      : {stats['original_size_bytes']} bytes",
            f"  New size           : {stats['new_size_bytes']} bytes",
            f"  Bytes saved        : {stats['bytes_saved']}",
            f"  Chunks removed     : {stats['removed_chunks']}",
        ]
        if stats["removed_chunk_types"]:
            lines.append("  Removed types      : " + ", ".join(stats["removed_chunk_types"]))
        if stats["trailing_bytes_removed"]:
            lines.append(
                f"  Trailing bytes     : {stats['trailing_bytes_removed']} removed"
            )
        return "\n".join(lines)
