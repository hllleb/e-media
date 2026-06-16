"""PNGParser – reads a PNG file and returns a PNGFile object."""

import os
from .reader import PNGReader
from .signature import PNGSignature
from .chunk import Chunk
from .chunks import chunk_factory
from .png_file import PNGFile


class PNGParser:
    """
    Orchestrates the full parse of a PNG binary file.

    Parsing steps:
        1. Open the file with PNGReader.
        2. Read and validate the 8-byte PNG signature.
        3. Read chunks sequentially until IEND is encountered or EOF.
        4. Record byte offsets for every chunk (length + type + data + CRC).
        5. Detect any trailing bytes after IEND (potential hidden data).
        6. Return a populated PNGFile object.
    """

    def parse(self, path: str) -> PNGFile:
        """
        Parse the PNG file at *path* and return a :class:`PNGFile`.

        Raises:
            FileNotFoundError  – if *path* does not exist.
            ValueError         – if the file is not a valid PNG.
            EOFError           – if the file is truncated mid-chunk.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path!r}")

        reader = PNGReader(path)

        signature = self._parse_signature(reader)
        chunks, chunks_pos = self._parse_chunks(reader)
        trailing_bytes = self._read_trailing(reader)

        return PNGFile(
            path=path,
            signature=signature,
            chunks=chunks,
            trailing_bytes=trailing_bytes,
            chunks_pos=chunks_pos,
        )

    # ------------------------------------------------------------------
    # Internal parsing stages
    # ------------------------------------------------------------------

    def _parse_signature(self, reader: PNGReader) -> PNGSignature:
        sig = PNGSignature.from_reader(reader)
        sig.validate()
        return sig

    def _parse_chunks(self, reader: PNGReader) -> tuple[list[Chunk], list[tuple[int, int]]]:
        chunks: list[Chunk] = []
        chunks_pos: list[tuple[int, int]] = []

        while not reader.at_end:
            if reader.remaining < 12:
                break

            chunk_start = reader.pos
            length = reader.read_uint32()
            type_bytes = reader.read(4)
            type_code = type_bytes.decode("ascii", errors="replace")
            raw_data = reader.read(length)
            crc_raw = reader.read_uint32()
            chunk_end = reader.pos - 1

            chunk = chunk_factory(type_code, length, raw_data, crc_raw)
            chunks.append(chunk)
            chunks_pos.append((chunk_start, chunk_end))

            if type_code == "IEND":
                break

        return chunks, chunks_pos

    def _read_trailing(self, reader: PNGReader) -> bytes:
        """
        Return any bytes remaining after the IEND chunk.
        Non-empty trailing bytes may indicate hidden/appended data.
        """
        return reader.data[reader.pos :]
