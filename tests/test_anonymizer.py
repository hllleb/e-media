"""Tests for PNGAnonymizer."""

from png_parser import PNGAnonymizer, PNGParser


def test_strip_ancillary_removes_metadata(rich_png_path):
    png = PNGParser().parse(rich_png_path)
    anonymizer = PNGAnonymizer()
    cleaned = anonymizer.strip_ancillary(png)

    assert len(cleaned.get_ancillary_chunks()) == 0
    assert len(cleaned.get_critical_chunks()) == 3
    assert cleaned.trailing_bytes == b""


def test_save_clean_preserves_pixels(rich_png_path, tmp_path):
    png = PNGParser().parse(rich_png_path)
    out = tmp_path / "clean.png"
    stats = PNGAnonymizer().save_clean(png, str(out))

    assert stats["removed_chunks"] == 5
    assert stats["trailing_bytes_removed"] == len(b"HIDDEN_AFTER_IEND")
    assert "gAMA" in stats["removed_chunk_types"]

    cleaned = PNGParser().parse(str(out))
    assert png.get_raw_pixels() == cleaned.get_raw_pixels()


def test_anonymizer_report_format(rich_png_path, tmp_path):
    png = PNGParser().parse(rich_png_path)
    out = tmp_path / "clean2.png"
    stats = PNGAnonymizer().save_clean(png, str(out))
    report = PNGAnonymizer().report(stats)
    assert "Anonymization complete" in report
    assert str(out) in report
