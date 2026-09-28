import numpy as np

# Single word


def test_matches_correct_location_and_preserves_needle_size(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["CODE"])
    needle_h, needle_w = needle.shape[:2]
    haystack = blank_haystack()
    paste(haystack, render_lines(["HELP"]), 50, 50)
    paste(haystack, needle, 300, 200)
    paste(haystack, render_lines(["ABOUT"]), 50, 400)

    matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

    assert len(matches) == 1
    corners, _, score = matches[0]
    tl, tr, br, bl = corners

    assert score >= 0.8
    assert abs(tl[0] - 300) <= 5
    assert abs(tl[1] - 200) <= 5
    # Box is the needle's own rectangle, translated only - no scaling.
    assert abs((tr[0] - tl[0]) - needle_w) <= 2
    assert abs((bl[1] - tl[1]) - needle_h) <= 2


def test_small_word_at_the_same_size_still_matches(ocr, render_lines, blank_haystack, paste, params):
    # A small needle's own detected box carries more relative detector noise - it must not
    # be rejected by the size-consistency guard just for being small.
    needle = render_lines(["OK"], font_size=14, padding=6)
    needle_h, needle_w = needle.shape[:2]
    haystack = blank_haystack()
    paste(haystack, needle, 300, 200)
    paste(haystack, render_lines(["CANCEL"], font_size=14, padding=6), 300, 260)

    matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

    assert len(matches) == 1


def test_same_text_at_a_different_font_size_is_rejected(ocr, render_lines, blank_haystack, paste, params):
    # Same word, rendered much bigger in the haystack (different UI scale/zoom) - text
    # similarity would be 1.0, but the size mismatch means it isn't a real translation-only
    # match under our no-scale assumption, so it must be dropped rather than kept with a
    # box sized to the needle (which would then be wrong).
    needle = render_lines(["SETTINGS"], font_size=20)
    haystack = blank_haystack()
    paste(haystack, render_lines(["SETTINGS"], font_size=48), 100, 100)

    assert ocr.compute(needle, haystack, target=(10, 10), params=params()) == []


def test_target_offset_preserved_when_not_centered(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["CODE"], padding=20)
    target = (5, 5)  # e.g. an icon near the needle's top-left, far from the text itself
    haystack = blank_haystack()
    paste(haystack, needle, 150, 100)

    matches = ocr.compute(needle, haystack, target=target, params=params())

    assert len(matches) == 1
    _, (tx, ty), _ = matches[0]
    # A few pixels of slack for the detector's own text-box imprecision - the offset
    # math itself is exact, but the detected text box it anchors on isn't pixel-perfect.
    assert abs(tx - (150 + target[0])) <= 10
    assert abs(ty - (100 + target[1])) <= 10


def test_no_text_in_needle_returns_empty(ocr, render_lines, blank_haystack, paste, params):
    needle = np.full((60, 200, 3), 250, dtype=np.uint8)
    haystack = blank_haystack()
    paste(haystack, render_lines(["CODE"]), 300, 200)

    assert ocr.compute(needle, haystack, target=(100, 30), params=params()) == []


def test_multiple_occurrences_return_multiple_matches(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["MENU"])
    needle_h, needle_w = needle.shape[:2]
    haystack = blank_haystack()
    paste(haystack, needle, 50, 50)
    paste(haystack, needle, 500, 400)
    paste(haystack, render_lines(["OTHER"]), 50, 400)

    matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

    assert len(matches) == 2


# Multi-word and multi-line


def test_multi_word_needle_on_one_line_matches(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["EXPAND TO LEVEL"])
    needle_h, needle_w = needle.shape[:2]
    haystack = blank_haystack()
    paste(haystack, needle, 200, 150)
    paste(haystack, render_lines(["COLLAPSE ALL"]), 200, 400)

    matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

    assert len(matches) == 1


def test_multi_line_needle_block_matches_multi_line_haystack_block(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["PREMIER", "CHOIX"])
    needle_h, needle_w = needle.shape[:2]
    haystack = blank_haystack()
    paste(haystack, render_lines(["AUTRE"]), 50, 50)
    paste(haystack, needle, 250, 250)
    paste(haystack, render_lines(["TEXTE"]), 50, 450)

    matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

    assert len(matches) == 1
    corners, _, _ = matches[0]
    tl, _, br, _ = corners
    # Union box covers both lines, close to the full needle height.
    assert abs((br[1] - tl[1]) - needle_h) <= 4


def test_needle_matches_only_part_of_a_longer_haystack_line(ocr, render_lines, blank_haystack, paste, params):
    # The needle is just "CHOIX", but the haystack line reads "PREMIER CHOIX" - the match
    # must still be found, tightly boxed around "CHOIX" only, not the whole line.
    needle = render_lines(["CHOIX"])
    needle_h, needle_w = needle.shape[:2]
    haystack = blank_haystack()
    full_line = render_lines(["PREMIER CHOIX"])
    paste(haystack, full_line, 200, 200)
    paste(haystack, render_lines(["AUTRE TEXTE"]), 200, 400)

    matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

    assert len(matches) == 1
    corners, _, _ = matches[0]
    tl, tr, _, _ = corners
    matched_width = tr[0] - tl[0]
    full_line_width = full_line.shape[1]
    # The matched box should be noticeably narrower than the whole "PREMIER CHOIX" line,
    # and it should sit on the right-hand side of it (where "CHOIX" actually is).
    assert matched_width < full_line_width * 0.7
    assert tl[0] > 200 + full_line_width * 0.3


def test_needle_matches_subset_of_a_larger_stacked_block(ocr, render_lines, blank_haystack, paste, params):
    # The haystack has 4 tightly stacked lines (one adjacency cluster); the needle only
    # covers the middle two - the match must not swallow the whole 4-line stack.
    stack = render_lines(["ITEM ONE", "ITEM TWO", "ITEM THREE", "ITEM FOUR"])
    needle = render_lines(["ITEM TWO", "ITEM THREE"])
    needle_h, needle_w = needle.shape[:2]
    haystack = blank_haystack()
    paste(haystack, stack, 200, 100)

    matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

    assert len(matches) == 1
    corners, _, _ = matches[0]
    tl, _, br, _ = corners
    matched_height = br[1] - tl[1]
    # Close to the needle's own (2-line) height, well under the full 4-line stack's height.
    assert abs(matched_height - needle_h) <= 6
    assert matched_height < stack.shape[0] * 0.7


# Threshold


def test_similarity_below_threshold_yields_no_match(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["SAVE"])
    haystack = blank_haystack()
    paste(haystack, render_lines(["SAFE"]), 300, 200)

    matches = ocr.compute(needle, haystack, target=(10, 10), params=params(confidence_threshold=0.95))

    assert matches == []


def test_lowering_threshold_recovers_the_match(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["SAVE"])
    haystack = blank_haystack()
    paste(haystack, render_lines(["SAFE"]), 300, 200)

    matches = ocr.compute(needle, haystack, target=(10, 10), params=params(confidence_threshold=0.6))

    assert len(matches) == 1


def test_matches_regardless_of_case(ocr, render_lines, blank_haystack, paste, params):
    needle = render_lines(["Code"])
    haystack = blank_haystack()
    paste(haystack, render_lines(["code"]), 300, 200)

    matches = ocr.compute(needle, haystack, target=(10, 10), params=params(confidence_threshold=0.8))

    assert len(matches) == 1


# Defaults


def test_missing_params_fall_back_to_defaults(ocr, render_lines, blank_haystack, paste):
    needle = render_lines(["TEST"])
    haystack = blank_haystack()
    paste(haystack, render_lines(["TEST"]), 300, 200)

    assert len(ocr.compute(needle, haystack, target=(10, 10), params=None)) == 1
    assert len(ocr.compute(needle, haystack, target=(10, 10), params={})) == 1
