"""Encrypt and decrypt PNG IDAT payloads using raw RSA block modes."""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from encryption.cbc import CBCEncryptor
from encryption.ecb import ECBEncryptor
from png_parser.png_file import PNGFile
from rsa import RSACipher, RSAKeyPair, load_keypair


class BlockMode(str, Enum):
    ECB = "ecb"
    CBC = "cbc"


class DataVariant(str, Enum):
    """
    Which IDAT representation to encrypt.

    FILTERED  – method A: decompress → encrypt → recompress into IDAT
    COMPRESSED – method B: encrypt zlib stream directly
    """

    FILTERED = "filtered"
    COMPRESSED = "compressed"


@dataclass
class EncryptResult:
    png: PNGFile
    iv: bytes | None
    plaintext_len: int
    ciphertext_len: int


@dataclass
class DecryptResult:
    png: PNGFile
    plaintext: bytes


def _extract_plaintext(png: PNGFile, variant: DataVariant) -> bytes:
    if variant == DataVariant.FILTERED:
        return png.get_filtered_idat_bytes()
    return png.get_idat_compressed()


def _apply_max_bytes(data: bytes, max_bytes: int | None) -> bytes:
    if max_bytes is not None and max_bytes >= 0:
        return data[:max_bytes]
    return data


def _pack_idat_payload(payload: bytes, variant: DataVariant) -> bytes:
    """Store encrypted or decrypted bytes in IDAT (method A recompresses)."""
    if variant == DataVariant.FILTERED:
        return zlib.compress(payload, level=9)
    return payload


def _unpack_idat_payload(stored: bytes, variant: DataVariant) -> bytes:
    """Read bytes from IDAT before decryption (method A decompresses first)."""
    if variant == DataVariant.FILTERED:
        return zlib.decompress(stored)
    return stored


def encrypt_idat(
    png: PNGFile,
    public_key: RSAKeyPair | str | Path,
    *,
    mode: BlockMode = BlockMode.ECB,
    variant: DataVariant = DataVariant.FILTERED,
    iv: bytes | None = None,
    max_bytes: int | None = None,
) -> EncryptResult:
    """
    Encrypt the IDAT payload of *png*.

    Method A (filtered): encrypt decompressed scanline bytes, zlib-compress ciphertext.
    Method B (compressed): encrypt raw zlib stream, store ciphertext directly.
    """
    if isinstance(public_key, (str, Path)):
        public_key = load_keypair(public_key)

    cipher = RSACipher(public_key)
    plaintext = _apply_max_bytes(_extract_plaintext(png, variant), max_bytes)

    iv_used: bytes | None = None
    if mode == BlockMode.ECB:
        ciphertext = ECBEncryptor(cipher).encrypt(plaintext)
    elif mode == BlockMode.CBC:
        cbc = CBCEncryptor(cipher, iv=iv)
        ciphertext, iv_used = cbc.encrypt(plaintext, iv=iv)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    stored = _pack_idat_payload(ciphertext, variant)
    encrypted_png = png.replace_idat(stored)
    return EncryptResult(
        png=encrypted_png,
        iv=iv_used,
        plaintext_len=len(plaintext),
        ciphertext_len=len(ciphertext),
    )


def decrypt_idat(
    png: PNGFile,
    private_key: RSAKeyPair | str | Path,
    *,
    mode: BlockMode = BlockMode.ECB,
    variant: DataVariant = DataVariant.FILTERED,
    iv: bytes | None = None,
) -> DecryptResult:
    """
    Decrypt IDAT and restore a valid PNG IDAT payload.

    Method A: decompress IDAT → decrypt → recompress filtered bytes.
    Method B: decrypt ciphertext bytes directly.
    """
    if isinstance(private_key, (str, Path)):
        private_key = load_keypair(private_key)

    cipher = RSACipher(private_key)
    stored = png.get_idat_compressed()
    ciphertext = _unpack_idat_payload(stored, variant)

    if mode == BlockMode.ECB:
        plaintext = ECBEncryptor(cipher).decrypt(ciphertext)
    elif mode == BlockMode.CBC:
        if iv is None:
            raise ValueError("CBC decryption requires an IV.")
        plaintext = CBCEncryptor(cipher).decrypt(ciphertext, iv)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    restored = png.replace_idat(_pack_idat_payload(plaintext, variant))
    return DecryptResult(png=restored, plaintext=plaintext)


def save_iv(iv: bytes, path: str | Path) -> None:
    """Write IV as hex text."""
    Path(path).write_text(iv.hex(), encoding="ascii")


def load_iv(path: str | Path) -> bytes:
    """Read IV from hex text file."""
    return bytes.fromhex(Path(path).read_text(encoding="ascii").strip())


def roundtrip_plaintext(
    png: PNGFile,
    key: RSAKeyPair,
    *,
    mode: BlockMode,
    variant: DataVariant,
    max_bytes: int | None = None,
) -> bytes:
    """Encrypt then decrypt and return recovered plaintext bytes."""
    enc = encrypt_idat(
        png,
        key,
        mode=mode,
        variant=variant,
        max_bytes=max_bytes,
    )
    dec = decrypt_idat(
        enc.png,
        key,
        mode=mode,
        variant=variant,
        iv=enc.iv,
    )
    return dec.plaintext
