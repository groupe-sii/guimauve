from guimauve.detection import ocr as ocr_module


def test_splits_line_box_proportionally_by_character_count():
    line_box = (100, 10, 200, 30)  # width=100, 4 total chars -> 25px per char
    tokens = ocr_module._proportional_tokens(["AB", "CD"], line_box)

    assert [t[0] for t in tokens] == ["AB", "CD"]
    assert tokens[0][1] == (100, 10, 150, 30)
    assert tokens[1][1] == (150, 10, 200, 30)


def test_marks_had_space_only_when_a_whitespace_token_precedes():
    # Mirrors real OCR output where an accented letter can be tokenized apart from the rest
    # of its word with no whitespace token in between (e.g. "E" + "clipse"), while a real
    # word boundary does have one (a literal " " token).
    tokens = ocr_module._proportional_tokens(["E", "clipse", " ", "solaire"], (0, 0, 100, 20))

    assert [t[0] for t in tokens] == ["E", "clipse", "solaire"]
    assert [t[2] for t in tokens] == [False, False, True]


def test_ignores_word_level_pixel_boxes_entirely():
    # _readtext must not depend on PaddleOCR's own per-word boxes for geometry (they can be
    # badly wrong for isolated accented letters) - _proportional_tokens only takes word
    # strings and the line's own box, no word-box argument exists to (mis)use.
    import inspect

    assert list(inspect.signature(ocr_module._proportional_tokens).parameters) == ["words", "line_box"]
