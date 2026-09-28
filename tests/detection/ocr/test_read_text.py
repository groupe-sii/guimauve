import numpy as np
import pytest

from guimauve.enums import OcrFidelity


def test_reads_single_line(ocr, render_lines):
    image = render_lines(["Hello world"])

    assert ocr.read_text_on_image(image, fidelity=OcrFidelity.FAST) == "Hello world"


def test_joins_multiple_lines_with_newline_in_reading_order(ocr, render_lines):
    image = render_lines(["First line", "Second line", "Third line"])

    text = ocr.read_text_on_image(image, fidelity=OcrFidelity.FAST)

    assert text == "First line\nSecond line\nThird line"


def test_restricts_to_the_given_area(ocr, render_lines, blank_haystack, paste):
    haystack = blank_haystack()
    paste(haystack, render_lines(["Outside"]), 50, 50)
    paste(haystack, render_lines(["Inside"]), 300, 300)

    text = ocr.read_text_on_image(haystack, area=(280, 280, 150, 80), fidelity=OcrFidelity.FAST)

    assert text == "Inside"


def test_no_text_returns_empty_string(ocr):
    blank = np.full((60, 200, 3), 250, dtype=np.uint8)

    assert ocr.read_text_on_image(blank, fidelity=OcrFidelity.FAST) == ""


def test_fidelity_is_required(ocr, blank_haystack):
    with pytest.raises(TypeError):
        ocr.read_text_on_image(blank_haystack())


def test_fidelity_is_passed_through_to_readtext(ocr, monkeypatch, blank_haystack):
    captured = {}

    def fake_readtext(image, fidelity):
        captured["fidelity"] = fidelity
        return []

    monkeypatch.setattr(ocr, "_readtext", fake_readtext)

    ocr.read_text_on_image(blank_haystack(), fidelity=OcrFidelity.FAST)

    assert captured["fidelity"] == OcrFidelity.FAST
