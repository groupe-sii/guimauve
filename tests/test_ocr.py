import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from guimauve.detection import ocr as ocr_module
from guimauve.detection.ocr import Ocr
from guimauve.enums import OcrFidelity


def _font(size):
    return ImageFont.load_default(size=size)


def render_lines(lines, font_size=26, padding=12, line_gap=8, bg=(245, 245, 245), fg=(15, 15, 15)):
    """Render one or more lines of text on a tightly-cropped canvas. Returns a BGR np.ndarray."""
    font = _font(font_size)
    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    sizes = [dummy.textbbox((0, 0), line, font=font)[2:] for line in lines]

    width = max(w for w, h in sizes) + padding * 2
    line_height = max(h for w, h in sizes)
    height = line_height * len(lines) + line_gap * (len(lines) - 1) + padding * 2

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    y = padding
    for line in lines:
        draw.text((padding, y), line, font=font, fill=fg)
        y += line_height + line_gap

    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def blank_haystack(width=800, height=600, bg=(250, 250, 250)):
    return np.full((height, width, 3), bg, dtype=np.uint8)


def paste(haystack, patch, x, y):
    h, w = patch.shape[:2]
    haystack[y : y + h, x : x + w] = patch
    return haystack


def params(**overrides):
    base = {"fidelity": OcrFidelity.FAST, "confidence_threshold": 0.8}
    base.update(overrides)
    return base


@pytest.fixture(scope="module")
def ocr():
    return Ocr()


class TestSimilarity:
    def test_case_insensitive(self):
        assert Ocr._similarity("Code", "code") == 1.0


class TestProportionalTokens:
    def test_splits_line_box_proportionally_by_character_count(self):
        line_box = (100, 10, 200, 30)  # width=100, 4 total chars -> 25px per char
        tokens = ocr_module._proportional_tokens(["AB", "CD"], line_box)

        assert [t[0] for t in tokens] == ["AB", "CD"]
        assert tokens[0][1] == (100, 10, 150, 30)
        assert tokens[1][1] == (150, 10, 200, 30)

    def test_marks_had_space_only_when_a_whitespace_token_precedes(self):
        # Mirrors real OCR output where an accented letter can be tokenized apart from the rest
        # of its word with no whitespace token in between (e.g. "E" + "clipse"), while a real
        # word boundary does have one (a literal " " token).
        tokens = ocr_module._proportional_tokens(["E", "clipse", " ", "solaire"], (0, 0, 100, 20))

        assert [t[0] for t in tokens] == ["E", "clipse", "solaire"]
        assert [t[2] for t in tokens] == [False, False, True]

    def test_ignores_word_level_pixel_boxes_entirely(self):
        # _readtext must not depend on PaddleOCR's own per-word boxes for geometry (they can be
        # badly wrong for isolated accented letters) - _proportional_tokens only takes word
        # strings and the line's own box, no word-box argument exists to (mis)use.
        import inspect

        assert list(inspect.signature(ocr_module._proportional_tokens).parameters) == ["words", "line_box"]


class TestComputeSingleWord:
    def test_matches_correct_location_and_preserves_needle_size(self, ocr):
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

    def test_small_word_at_the_same_size_still_matches(self, ocr):
        # A small needle's own detected box carries more relative detector noise - it must not
        # be rejected by the size-consistency guard just for being small.
        needle = render_lines(["OK"], font_size=14, padding=6)
        needle_h, needle_w = needle.shape[:2]
        haystack = blank_haystack()
        paste(haystack, needle, 300, 200)
        paste(haystack, render_lines(["CANCEL"], font_size=14, padding=6), 300, 260)

        matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

        assert len(matches) == 1

    def test_same_text_at_a_different_font_size_is_rejected(self, ocr):
        # Same word, rendered much bigger in the haystack (different UI scale/zoom) - text
        # similarity would be 1.0, but the size mismatch means it isn't a real translation-only
        # match under our no-scale assumption, so it must be dropped rather than kept with a
        # box sized to the needle (which would then be wrong).
        needle = render_lines(["SETTINGS"], font_size=20)
        haystack = blank_haystack()
        paste(haystack, render_lines(["SETTINGS"], font_size=48), 100, 100)

        assert ocr.compute(needle, haystack, target=(10, 10), params=params()) == []

    def test_target_offset_preserved_when_not_centered(self, ocr):
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

    def test_no_text_in_needle_returns_empty(self, ocr):
        needle = np.full((60, 200, 3), 250, dtype=np.uint8)
        haystack = blank_haystack()
        paste(haystack, render_lines(["CODE"]), 300, 200)

        assert ocr.compute(needle, haystack, target=(100, 30), params=params()) == []

    def test_multiple_occurrences_return_multiple_matches(self, ocr):
        needle = render_lines(["MENU"])
        needle_h, needle_w = needle.shape[:2]
        haystack = blank_haystack()
        paste(haystack, needle, 50, 50)
        paste(haystack, needle, 500, 400)
        paste(haystack, render_lines(["OTHER"]), 50, 400)

        matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

        assert len(matches) == 2


class TestComputeMultiWordAndMultiLine:
    def test_multi_word_needle_on_one_line_matches(self, ocr):
        needle = render_lines(["EXPAND TO LEVEL"])
        needle_h, needle_w = needle.shape[:2]
        haystack = blank_haystack()
        paste(haystack, needle, 200, 150)
        paste(haystack, render_lines(["COLLAPSE ALL"]), 200, 400)

        matches = ocr.compute(needle, haystack, target=(needle_w // 2, needle_h // 2), params=params())

        assert len(matches) == 1

    def test_multi_line_needle_block_matches_multi_line_haystack_block(self, ocr):
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

    def test_needle_matches_only_part_of_a_longer_haystack_line(self, ocr):
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


    def test_needle_matches_subset_of_a_larger_stacked_block(self, ocr):
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


class TestComputeThreshold:
    def test_similarity_below_threshold_yields_no_match(self, ocr):
        needle = render_lines(["SAVE"])
        haystack = blank_haystack()
        paste(haystack, render_lines(["SAFE"]), 300, 200)

        matches = ocr.compute(
            needle, haystack, target=(10, 10), params=params(confidence_threshold=0.95)
        )

        assert matches == []

    def test_lowering_threshold_recovers_the_match(self, ocr):
        needle = render_lines(["SAVE"])
        haystack = blank_haystack()
        paste(haystack, render_lines(["SAFE"]), 300, 200)

        matches = ocr.compute(
            needle, haystack, target=(10, 10), params=params(confidence_threshold=0.6)
        )

        assert len(matches) == 1

    def test_matches_regardless_of_case(self, ocr):
        needle = render_lines(["Code"])
        haystack = blank_haystack()
        paste(haystack, render_lines(["code"]), 300, 200)

        matches = ocr.compute(needle, haystack, target=(10, 10), params=params(confidence_threshold=0.8))

        assert len(matches) == 1


class TestComputeDefaults:
    def test_missing_params_fall_back_to_defaults(self, ocr):
        needle = render_lines(["TEST"])
        haystack = blank_haystack()
        paste(haystack, render_lines(["TEST"]), 300, 200)

        assert len(ocr.compute(needle, haystack, target=(10, 10), params=None)) == 1
        assert len(ocr.compute(needle, haystack, target=(10, 10), params={})) == 1


class TestReadTextOnImage:
    def test_reads_single_line(self, ocr):
        image = render_lines(["Hello world"])

        assert ocr.read_text_on_image(image, fidelity=OcrFidelity.FAST) == "Hello world"

    def test_joins_multiple_lines_with_newline_in_reading_order(self, ocr):
        image = render_lines(["First line", "Second line", "Third line"])

        text = ocr.read_text_on_image(image, fidelity=OcrFidelity.FAST)

        assert text == "First line\nSecond line\nThird line"

    def test_restricts_to_the_given_area(self, ocr):
        haystack = blank_haystack()
        paste(haystack, render_lines(["Outside"]), 50, 50)
        paste(haystack, render_lines(["Inside"]), 300, 300)

        text = ocr.read_text_on_image(haystack, area=(280, 280, 150, 80), fidelity=OcrFidelity.FAST)

        assert text == "Inside"

    def test_no_text_returns_empty_string(self, ocr):
        blank = np.full((60, 200, 3), 250, dtype=np.uint8)

        assert ocr.read_text_on_image(blank, fidelity=OcrFidelity.FAST) == ""

    def test_fidelity_is_required(self, ocr):
        with pytest.raises(TypeError):
            ocr.read_text_on_image(blank_haystack())

    def test_fidelity_is_passed_through_to_readtext(self, ocr, monkeypatch):
        captured = {}

        def fake_readtext(image, fidelity):
            captured["fidelity"] = fidelity
            return []

        monkeypatch.setattr(ocr, "_readtext", fake_readtext)

        ocr.read_text_on_image(blank_haystack(), fidelity=OcrFidelity.FAST)

        assert captured["fidelity"] == OcrFidelity.FAST


def locate(ocr, image, text, area=None, fidelity=OcrFidelity.FAST, confidence_threshold=0.8):
    return ocr.locate_text_on_image(image, text, fidelity, confidence_threshold, area=area)


class TestLocateTextOnImage:
    def test_locates_a_single_occurrence(self, ocr):
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

    def test_locates_multiple_occurrences(self, ocr):
        haystack = blank_haystack()
        item = render_lines(["Menu"])
        paste(haystack, item, 50, 50)
        paste(haystack, item, 500, 400)
        paste(haystack, render_lines(["Other"]), 50, 400)

        matches = locate(ocr, haystack, "Menu")

        assert len(matches) == 2

    def test_locates_part_of_a_longer_line(self, ocr):
        haystack = blank_haystack()
        paste(haystack, render_lines(["PREMIER CHOIX"]), 200, 200)

        matches = locate(ocr, haystack, "CHOIX")

        assert len(matches) == 1

    def test_no_size_restriction_unlike_compute(self, ocr):
        # Same text, rendered much bigger - compute() would reject this via _consistent_size,
        # but there is no needle here to size-check against, so it must still be found.
        haystack = blank_haystack()
        paste(haystack, render_lines(["Settings"], font_size=48), 100, 100)

        matches = locate(ocr, haystack, "Settings")

        assert len(matches) == 1

    def test_restricts_to_area_and_offsets_result_back(self, ocr):
        haystack = blank_haystack()
        paste(haystack, render_lines(["Outside"]), 50, 50)
        paste(haystack, render_lines(["Inside"]), 300, 300)

        matches = locate(ocr, haystack, "Inside", area=(280, 280, 150, 80))

        assert len(matches) == 1
        assert matches[0].box.tl.x > 280 and matches[0].box.tl.y > 280

    def test_below_threshold_returns_no_match(self, ocr):
        haystack = blank_haystack()
        paste(haystack, render_lines(["SAFE"]), 300, 200)

        matches = locate(ocr, haystack, "SAVE", confidence_threshold=0.99)

        assert matches == []

    def test_fidelity_and_threshold_are_required(self, ocr):
        with pytest.raises(TypeError):
            ocr.locate_text_on_image(blank_haystack(), "Settings")


class TestGetEngineOfflineResolution:
    @staticmethod
    def _fresh_ocr():
        instance = object.__new__(Ocr)
        Ocr.__init__(instance)
        return instance

    def test_uses_vendored_model_dir_when_present(self, monkeypatch, tmp_path):
        det_name, rec_name = ocr_module._PADDLE_MODELS[OcrFidelity.FAST]
        det_dir = tmp_path / "official_models" / det_name
        rec_dir = tmp_path / "official_models" / rec_name
        det_dir.mkdir(parents=True)
        rec_dir.mkdir(parents=True)
        (det_dir / "inference.json").write_text("{}")
        (rec_dir / "inference.json").write_text("{}")

        monkeypatch.setattr(ocr_module, "_MODELS_ROOT", tmp_path)

        captured = {}

        def fake_paddle_ocr(**kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr(ocr_module, "PaddleOCR", fake_paddle_ocr)

        self._fresh_ocr()._get_engine(OcrFidelity.FAST)

        assert captured["text_detection_model_dir"] == str(det_dir)
        assert captured["text_recognition_model_dir"] == str(rec_dir)
        assert captured["text_detection_model_name"] == det_name
        assert captured["text_recognition_model_name"] == rec_name

    def test_raises_clear_error_when_missing_locally_and_download_fails(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ocr_module, "_MODELS_ROOT", tmp_path)

        def fake_paddle_ocr(**kwargs):
            raise Exception("No available model hosting platforms detected.")

        monkeypatch.setattr(ocr_module, "PaddleOCR", fake_paddle_ocr)

        with pytest.raises(RuntimeError) as exc_info:
            self._fresh_ocr()._get_engine(OcrFidelity.FAST)

        assert str(tmp_path) in str(exc_info.value)
