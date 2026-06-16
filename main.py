"""
PNG Analyzer – command-line entry point.

Usage examples:

    # Show full metadata report
    python main.py info image.png

    # Anonymize (remove all ancillary chunks + trailing data)
    python main.py anonymize image.png -o image_clean.png

    # Display FFT spectrum and save the figure
    python main.py fft image.png --save spectrum.png

    # Run FFT self-test with a synthetic sine-wave image
    python main.py fft --verify
"""

import argparse
import sys

from png_parser import PNGParser, PNGAnonymizer, FFTAnalyzer


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


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="png_analyzer",
        description="Manual PNG parser – E-Media Project 1",
    )
    sub = root.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # --- info ---
    p_info = sub.add_parser("info", help="Display full PNG metadata report")
    p_info.add_argument("file", help="Path to PNG file")
    p_info.set_defaults(func=cmd_info)

    # --- anonymize ---
    p_anon = sub.add_parser(
        "anonymize", help="Strip ancillary chunks and hidden data"
    )
    p_anon.add_argument("file", help="Path to PNG file")
    p_anon.add_argument(
        "-o", "--output",
        help="Output path (default: <input>_clean.png)",
    )
    p_anon.set_defaults(func=cmd_anonymize)

    # --- fft ---
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

    return root


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
