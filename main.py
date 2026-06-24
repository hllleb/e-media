"""
PNG Analyzer – command-line entry point.

Project 1: info, anonymize, fft
Project 2: keygen, encrypt, decrypt, compare, visualize
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from png_parser import PNGAnonymizer, PNGParser, FFTAnalyzer
from path_conventions import (
    default_decrypt_output,
    default_encrypt_output,
    default_iv_path,
    default_visualize_paths,
    ensure_out_dir,
)


def _print_compare_result(result, mode_label: str) -> None:
    print(f"Blocks compared: {result.blocks_compared}")
    print(f"Matching ciphertext blocks: {result.matching_blocks}")
    print(f"Our ciphertext size: {result.own_ciphertext_len} bytes")
    print(f"Reference ciphertext size: {result.reference_ciphertext_len} bytes")
    if result.all_match:
        print(f"Raw RSA-{mode_label}: ciphertext matches independent pow(m, e, n) reference.")
    else:
        print("Mismatch detected (unexpected for raw RSA).")
        if result.first_mismatch_index is not None:
            print(f"First differing block index: {result.first_mismatch_index}")


def _crypto_mode(value: str):
    from idat_processor import BlockMode

    return BlockMode(value.lower())


def _crypto_variant(value: str):
    from idat_processor import DataVariant

    return DataVariant(value.lower())


def cmd_info(args: argparse.Namespace) -> int:
    try:
        png = PNGParser().parse(args.file)
    except (FileNotFoundError, ValueError, EOFError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(png.display_info())
    return 0


def cmd_anonymize(args: argparse.Namespace) -> int:
    try:
        png = PNGParser().parse(args.file)
    except (FileNotFoundError, ValueError, EOFError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = args.output or args.file.replace(".png", "_clean.png")
    if output == args.file:
        output = args.file.replace(".png", "_clean.png")
        if output == args.file:
            output = args.file + ".clean.png"

    anonymizer = PNGAnonymizer()
    stats = anonymizer.save_clean(png, output)
    print(anonymizer.report(stats))
    return 0


def cmd_fft(args: argparse.Namespace) -> int:
    if args.verify:
        print("Running FFT validation with synthetic sine-wave image…")
        ok = FFTAnalyzer.verify_with_synthetic(frequency=8, show=not args.no_show)
        print(f"Validation result: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1

    if not args.file:
        print("Error: provide a PNG file or use --verify", file=sys.stderr)
        return 1

    try:
        png = PNGParser().parse(args.file)
    except (FileNotFoundError, ValueError, EOFError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    analyzer = FFTAnalyzer(png)
    analyzer.plot_spectrum(
        save_path=args.save,
        show=not args.no_show,
    )
    return 0


def cmd_keygen(args: argparse.Namespace) -> int:
    from rsa import generate_keypair, save_keypair

    key = generate_keypair(bits=args.bits)
    save_keypair(key, args.output)
    print(f"RSA key pair written to {args.output} ({args.bits}-bit modulus)")
    return 0


def cmd_encrypt(args: argparse.Namespace) -> int:
    from idat_processor import encrypt_idat, save_iv

    try:
        png = PNGParser().parse(args.file)
    except (FileNotFoundError, ValueError, EOFError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    iv_bytes = None
    if args.iv_file:
        from idat_processor import load_iv

        iv_bytes = load_iv(args.iv_file)

    try:
        result = encrypt_idat(
            png,
            args.public_key,
            mode=_crypto_mode(args.mode),
            variant=_crypto_variant(args.variant),
            iv=iv_bytes,
            max_bytes=args.max_bytes,
        )
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = args.output or str(
        default_encrypt_output(args.file, args.mode, args.variant)
    )
    ensure_out_dir()
    result.png.save(output)

    if result.iv is not None:
        iv_path = args.iv_out or str(default_iv_path(output))
        save_iv(result.iv, iv_path)
        print(f"IV written to {iv_path}")

    print(
        f"Encrypted {result.plaintext_len} bytes -> {result.ciphertext_len} bytes "
        f"({args.mode.upper()}, {args.variant})"
    )
    print(f"Saved {output}")
    return 0


def cmd_decrypt(args: argparse.Namespace) -> int:
    from idat_processor import decrypt_idat, load_iv

    try:
        png = PNGParser().parse(args.file)
    except (FileNotFoundError, ValueError, EOFError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    iv = None
    mode = _crypto_mode(args.mode)
    if mode == _crypto_mode("cbc"):
        iv_path = args.iv_file or str(default_iv_path(args.file))
        if not Path(iv_path).is_file():
            print(
                f"Error: CBC decryption requires IV file "
                f"(try {iv_path} or pass --iv-file)",
                file=sys.stderr,
            )
            return 1
        iv = load_iv(iv_path)

    try:
        result = decrypt_idat(
            png,
            args.private_key,
            mode=_crypto_mode(args.mode),
            variant=_crypto_variant(args.variant),
            iv=iv,
        )
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = args.output or str(
        default_decrypt_output(args.file, args.mode, args.variant)
    )
    ensure_out_dir()
    result.png.save(output)
    print(f"Decrypted {len(result.plaintext)} bytes -> {output}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    import secrets

    from encryption import CBCEncryptor, ECBEncryptor
    from idat_processor import DataVariant, load_iv
    from rsa import RSACipher, load_keypair
    from rsa_reference import compare_plaintext_encryption, compare_plaintext_encryption_cbc

    try:
        png = PNGParser().parse(args.file)
    except (FileNotFoundError, ValueError, EOFError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    key = load_keypair(args.public_key)
    variant = _crypto_variant(args.variant)
    if variant == DataVariant.FILTERED:
        plaintext = png.get_filtered_idat_bytes()
    else:
        plaintext = png.get_idat_compressed()

    if args.max_bytes is not None:
        plaintext = plaintext[: args.max_bytes]

    mode = _crypto_mode(args.mode)
    cipher = RSACipher(key)

    try:
        if mode == _crypto_mode("ecb"):
            own_ct = ECBEncryptor(cipher).encrypt(plaintext)
            result = compare_plaintext_encryption(key, plaintext, own_ct)
            _print_compare_result(result, "ECB")
        else:
            if args.iv_file:
                iv = load_iv(args.iv_file)
            else:
                iv = secrets.token_bytes(cipher.plaintext_block_size)
                print(f"Generated IV for compare (hex): {iv.hex()}")
            own_ct, _ = CBCEncryptor(cipher).encrypt(plaintext, iv=iv)
            result = compare_plaintext_encryption_cbc(key, plaintext, iv, own_ct)
            _print_compare_result(result, "CBC")
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    """Encrypt with ECB and CBC, save PNGs and optional comparison figure."""
    import numpy as np
    import matplotlib.pyplot as plt

    from idat_processor import BlockMode, encrypt_idat
    from rsa import load_keypair

    try:
        png = PNGParser().parse(args.file)
    except (FileNotFoundError, ValueError, EOFError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    key = load_keypair(args.public_key)
    variant = _crypto_variant(args.variant)
    ihdr = png.get_ihdr()
    w, h = ihdr.width, ihdr.height

    enc_ecb = encrypt_idat(
        png,
        key,
        mode=BlockMode.ECB,
        variant=variant,
        max_bytes=args.max_bytes,
    )
    enc_cbc = encrypt_idat(
        png,
        key,
        mode=BlockMode.CBC,
        variant=variant,
        max_bytes=args.max_bytes,
    )

    ecb_path, cbc_path, figure_path = default_visualize_paths(args.file)
    if args.output:
        stem = Path(args.output).stem
        out_dir = Path(args.output).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        ecb_path = out_dir / f"{stem}_ecb.png"
        cbc_path = out_dir / f"{stem}_cbc.png"
        figure_path = out_dir / f"{stem}_ecb_vs_cbc.png"
    else:
        ensure_out_dir()

    save_figure = args.save_figure or str(figure_path)

    enc_ecb.png.save(str(ecb_path))
    enc_cbc.png.save(str(cbc_path))
    if enc_cbc.iv is not None:
        from idat_processor import save_iv

        save_iv(enc_cbc.iv, str(default_iv_path(cbc_path)))

    print(f"ECB encrypted PNG: {ecb_path}")
    print(f"CBC encrypted PNG: {cbc_path}")

    if not args.no_save_figure:
        n_pixels = w * h

        def _reshape_idat(png_file) -> np.ndarray:
            data = png_file.get_idat_compressed()
            usable = data[:n_pixels]
            if len(usable) < n_pixels:
                padded = usable + bytes(n_pixels - len(usable))
            else:
                padded = usable
            return np.frombuffer(padded, dtype=np.uint8).reshape(h, w)

        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        axes[0].imshow(_reshape_idat(enc_ecb.png), cmap="gray", vmin=0, vmax=255)
        axes[0].set_title("RSA-ECB (IDAT ciphertext preview)")
        axes[0].axis("off")
        axes[1].imshow(_reshape_idat(enc_cbc.png), cmap="gray", vmin=0, vmax=255)
        axes[1].set_title("RSA-CBC (IDAT ciphertext preview)")
        axes[1].axis("off")
        fig.tight_layout()
        fig.savefig(save_figure, dpi=120)
        plt.close(fig)
        print(f"Comparison figure: {save_figure}")

    return 0


def _add_crypto_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--mode",
        choices=["ecb", "cbc"],
        default="ecb",
        help="Block encryption mode (default: ecb)",
    )
    parser.add_argument(
        "--variant",
        choices=["filtered", "compressed"],
        default="filtered",
        help="IDAT variant: filtered (A) or compressed (B)",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=None,
        help="Limit plaintext bytes encrypted (useful for large images)",
    )


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="png_analyzer",
        description="Manual PNG parser – E-Media Projects 1 & 2",
    )
    sub = root.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p_info = sub.add_parser("info", help="Display full PNG metadata report")
    p_info.add_argument("file", help="Path to PNG file")
    p_info.set_defaults(func=cmd_info)

    p_anon = sub.add_parser(
        "anonymize", help="Strip ancillary chunks and hidden data"
    )
    p_anon.add_argument("file", help="Path to PNG file")
    p_anon.add_argument(
        "-o", "--output",
        help="Output path (default: <input>_clean.png)",
    )
    p_anon.set_defaults(func=cmd_anonymize)

    p_fft = sub.add_parser("fft", help="Show 2-D FFT spectrum")
    p_fft.add_argument(
        "file",
        nargs="?",
        help="Path to PNG file (omit when using --verify)",
    )
    p_fft.add_argument(
        "--save",
        metavar="PATH",
        help="Save spectrum figure to this path",
    )
    p_fft.add_argument(
        "--no-show",
        action="store_true",
        help="Do not open an interactive matplotlib window",
    )
    p_fft.add_argument(
        "--verify",
        action="store_true",
        help="Run self-test using a synthetic sine-wave image",
    )
    p_fft.set_defaults(func=cmd_fft)

    p_keygen = sub.add_parser("keygen", help="Generate RSA key pair (JSON)")
    p_keygen.add_argument(
        "-o", "--output",
        default="keys/rsa2048.json",
        help="Output key file (default: keys/rsa2048.json)",
    )
    p_keygen.add_argument(
        "--bits",
        type=int,
        default=2048,
        help="Modulus size in bits (default: 2048)",
    )
    p_keygen.set_defaults(func=cmd_keygen)

    p_enc = sub.add_parser("encrypt", help="RSA-encrypt PNG IDAT data")
    p_enc.add_argument("file", help="Input PNG file")
    p_enc.add_argument("-o", "--output", help="Output encrypted PNG (default: out/<stem>_enc_<mode>_<variant>.png)")
    p_enc.add_argument(
        "--public-key",
        required=True,
        help="Path to JSON key file (uses n, e)",
    )
    p_enc.add_argument(
        "--iv-file",
        help="Use this IV for CBC (hex file); random if omitted",
    )
    p_enc.add_argument(
        "--iv-out",
        help="Where to write generated IV (default: <output>.iv for CBC)",
    )
    _add_crypto_args(p_enc)
    p_enc.set_defaults(func=cmd_encrypt)

    p_dec = sub.add_parser("decrypt", help="RSA-decrypt PNG IDAT data")
    p_dec.add_argument("file", help="Encrypted PNG file")
    p_dec.add_argument("-o", "--output", help="Output decrypted PNG (default: out/<stem>_dec_<mode>_<variant>.png)")
    p_dec.add_argument(
        "--private-key",
        required=True,
        help="Path to JSON key file (uses n, e, d)",
    )
    p_dec.add_argument(
        "--iv-file",
        help="IV hex file for CBC (default: <input>.iv)",
    )
    _add_crypto_args(p_dec)
    p_dec.set_defaults(func=cmd_decrypt)

    p_cmp = sub.add_parser(
        "compare",
        help="Compare own RSA encryption with independent pow(m,e,n) reference",
    )
    p_cmp.add_argument("file", help="Input PNG file")
    p_cmp.add_argument(
        "--public-key",
        required=True,
        help="Path to JSON key file",
    )
    p_cmp.add_argument(
        "--iv-file",
        help="IV for CBC compare (random IV generated if omitted)",
    )
    _add_crypto_args(p_cmp)
    p_cmp.set_defaults(func=cmd_compare)

    p_vis = sub.add_parser(
        "visualize",
        help="Encrypt with ECB and CBC, save encrypted PNGs",
    )
    p_vis.add_argument("file", help="Input PNG file")
    p_vis.add_argument(
        "-o", "--output",
        help="Output stem in out/ (default: input stem -> out/<stem>_ecb.png, …)",
    )
    p_vis.add_argument(
        "--public-key",
        required=True,
        help="Path to JSON key file",
    )
    p_vis.add_argument(
        "--save-figure",
        metavar="PATH",
        help="Comparison figure path (default: out/<stem>_ecb_vs_cbc.png)",
    )
    p_vis.add_argument(
        "--no-save-figure",
        action="store_true",
        help="Skip saving the side-by-side comparison figure",
    )
    _add_crypto_args(p_vis)
    p_vis.set_defaults(func=cmd_visualize)

    return root


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
