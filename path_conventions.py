"""Default output paths for Project 2 CLI commands."""

from __future__ import annotations

from pathlib import Path

OUT_DIR = Path("out")


def ensure_out_dir() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUT_DIR


def input_stem(file_path: str | Path) -> str:
    return Path(file_path).stem


def default_encrypt_output(
    file_path: str | Path,
    mode: str,
    variant: str,
) -> Path:
    """e.g. images/normal.png -> out/normal_enc_ecb_filtered.png"""
    ensure_out_dir()
    return OUT_DIR / f"{input_stem(file_path)}_enc_{mode.lower()}_{variant.lower()}.png"


def default_decrypt_output(
    file_path: str | Path,
    mode: str,
    variant: str,
) -> Path:
    """
    e.g. out/normal_enc_ecb_filtered.png -> out/normal_dec_ecb_filtered.png

    If the input name has no ``_enc_`` token, builds ``{stem}_dec_{mode}_{variant}.png``.
    """
    ensure_out_dir()
    stem = input_stem(file_path)
    if "_enc_" in stem:
        stem = stem.replace("_enc_", "_dec_", 1)
    else:
        stem = f"{stem}_dec_{mode.lower()}_{variant.lower()}"
    return OUT_DIR / f"{stem}.png"


def default_iv_path(for_png: str | Path) -> Path:
    """IV file beside encrypted PNG: ``<png>.iv``."""
    return Path(str(for_png) + ".iv")


def default_visualize_paths(file_path: str | Path) -> tuple[Path, Path, Path]:
    """
    Returns ``(ecb_png, cbc_png, comparison_figure)``.

    e.g. normal.png -> out/normal_ecb.png, out/normal_cbc.png, out/normal_ecb_vs_cbc.png
    """
    ensure_out_dir()
    stem = input_stem(file_path)
    return (
        OUT_DIR / f"{stem}_ecb.png",
        OUT_DIR / f"{stem}_cbc.png",
        OUT_DIR / f"{stem}_ecb_vs_cbc.png",
    )
