"""Tests for CLI default output path conventions."""

from pathlib import Path

from path_conventions import (
    default_decrypt_output,
    default_encrypt_output,
    default_iv_path,
    default_visualize_paths,
)


def test_default_encrypt_output():
    assert default_encrypt_output("images/normal.png", "ecb", "filtered") == Path(
        "out/normal_enc_ecb_filtered.png"
    )
    assert default_encrypt_output("normal.png", "cbc", "compressed") == Path(
        "out/normal_enc_cbc_compressed.png"
    )


def test_default_decrypt_output_from_enc_name():
    assert default_decrypt_output(
        "out/normal_enc_ecb_filtered.png", "ecb", "filtered"
    ) == Path("out/normal_dec_ecb_filtered.png")


def test_default_decrypt_output_plain_stem():
    assert default_decrypt_output("normal.png", "cbc", "compressed") == Path(
        "out/normal_dec_cbc_compressed.png"
    )


def test_default_iv_path():
    assert default_iv_path("out/normal_enc_cbc_filtered.png") == Path(
        "out/normal_enc_cbc_filtered.png.iv"
    )


def test_default_visualize_paths():
    ecb, cbc, fig = default_visualize_paths("images/normal.png")
    assert ecb == Path("out/normal_ecb.png")
    assert cbc == Path("out/normal_cbc.png")
    assert fig == Path("out/normal_ecb_vs_cbc.png")
