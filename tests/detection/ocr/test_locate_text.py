import pytest

from guimauve.enums import OcrFidelity


def locate(ocr, image, text, area=None, fidelity=OcrFidelity.FAST, confidence_threshold=0.8):
    return ocr.locate_text_on_image(image, text, fidelity, confidence_threshold, area=area)


def test_locates_a_single_occurrence(ocr, render_lines, blank_haystack, paste):
    haystack = blank_haystack()
    needle_like = render_lines(["Settings"])
    paste(haystack, needle_like, 300, 200)
    paste(haystack, render_lines(["Help"]), 50, 50)

    matches = locate(ocr, haystack, "Settings")

    assert len(matches) == 1
    match = matches[0]
    assert abs(match.box.tl.x - 300) <= 10
    assert abs(match.box.tl.y - 200) <= 10
    assert match.box.br.x > match.box.tl.x and match.box.br.y > match.box.tl.y
    # No needle here, so the target defaults to the matched box's own center.
    assert match.target.x == (match.box.tl.x + match.box.br.x) // 2
    assert match.target.y == (match.box.tl.y + match.box.br.y) // 2
    assert match.confidence >= 0.8


def test_locates_multiple_occurrences(ocr, render_lines, blank_haystack, paste):
    haystack = blank_haystack()
    item = render_lines(["Menu"])
    paste(haystack, item, 50, 50)
    paste(haystack, item, 500, 400)
    paste(haystack, render_lines(["Other"]), 50, 400)

    matches = locate(ocr, haystack, "Menu")

    assert len(matches) == 2


def test_locates_part_of_a_longer_line(ocr, render_lines, blank_haystack, paste):
    haystack = blank_haystack()
    paste(haystack, render_lines(["PREMIER CHOIX"]), 200, 200)

    matches = locate(ocr, haystack, "CHOIX")

    assert len(matches) == 1


def test_no_size_restriction_unlike_compute(ocr, render_lines, blank_haystack, paste):
    # Same text, rendered much bigger - compute() would reject this via _consistent_size,
    # but there is no needle here to size-check against, so it must still be found.
    haystack = blank_haystack()
    paste(haystack, render_lines(["Settings"], font_size=48), 100, 100)

    matches = locate(ocr, haystack, "Settings")

    assert len(matches) == 1


def test_restricts_to_area_and_offsets_result_back(ocr, render_lines, blank_haystack, paste):
    haystack = blank_haystack()
    paste(haystack, render_lines(["Outside"]), 50, 50)
    paste(haystack, render_lines(["Inside"]), 300, 300)

    matches = locate(ocr, haystack, "Inside", area=(280, 280, 150, 80))

    assert len(matches) == 1
    assert matches[0].box.tl.x > 280 and matches[0].box.tl.y > 280


def test_below_threshold_returns_no_match(ocr, render_lines, blank_haystack, paste):
    haystack = blank_haystack()
    paste(haystack, render_lines(["SAFE"]), 300, 200)

    matches = locate(ocr, haystack, "SAVE", confidence_threshold=0.99)

    assert matches == []


def test_fidelity_and_threshold_are_required(ocr, blank_haystack):
    with pytest.raises(TypeError):
        ocr.locate_text_on_image(blank_haystack(), "Settings")
