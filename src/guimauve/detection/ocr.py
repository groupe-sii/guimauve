import logging
import os
import tempfile
import warnings
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Optional

import cv2
import numpy as np

from guimauve.detection.detector import Detector, Match
from guimauve.enums import OcrFidelity

# Models are vendored under this directory. PaddleX reads its cache location once, at import
# time, so the env var must be set before paddleocr/paddlex is imported anywhere in the process.
_MODELS_ROOT = Path(__file__).parent / "paddleocr"
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(_MODELS_ROOT))


def _silence_ccache_probe() -> None:
    """paddle probes for ccache at import time via `os.path.exists` then a `where`/`which`
    subprocess; on Windows the latter leaks its own localized stderr message when ccache is
    missing, bypassing logging/warnings entirely. A dummy `ccache` file on PATH satisfies the
    first check, so that subprocess call never runs."""
    shim_dir = Path(tempfile.gettempdir()) / "guimauve_ccache_shim"
    shim_dir.mkdir(exist_ok=True)
    (shim_dir / "ccache").touch(exist_ok=True)
    os.environ["PATH"] = str(shim_dir) + os.pathsep + os.environ.get("PATH", "")


_silence_ccache_probe()

_PADDLE_LOGGERS = ("paddlex", "paddleocr")
_CCACHE_WARNING = "No ccache found"

# paddlex sets its own logger level unconditionally on import, so this must be captured
# *before* importing it - otherwise a level set on purpose beforehand is indistinguishable
# from paddlex's own default.
_paddle_loggers_preconfigured = any(logging.getLogger(name).level != logging.NOTSET for name in _PADDLE_LOGGERS)

from paddleocr import PaddleOCR  # noqa: E402


def set_paddleocr_verbose(enabled: bool = True) -> None:
    """
    Toggle PaddleOCR/PaddleX's own logging (model loading, download progress, missing-ccache
    notice, ...). Silenced by default so it doesn't bury guimauve's own logs - call with True
    to restore their normal output.

    :param enabled: True to restore PaddleOCR/PaddleX's normal logging, False to silence it
    """
    level = logging.INFO if enabled else logging.ERROR
    for name in _PADDLE_LOGGERS:
        logging.getLogger(name).setLevel(level)

    warnings.filterwarnings("default" if enabled else "ignore", message=_CCACHE_WARNING, category=UserWarning)


if not _paddle_loggers_preconfigured:
    set_paddleocr_verbose(False)

_PADDLE_MODELS = {
    OcrFidelity.FAST: ("PP-OCRv6_tiny_det", "PP-OCRv6_tiny_rec"),
    OcrFidelity.BALANCED: ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"),
    OcrFidelity.ACCURATE: ("PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"),
}

Box = tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
Token = tuple[str, Box, bool]  # (word_text, word_box, had_space_before)
Line = tuple[str, Box, float, list[Token]]  # (text, box, score, tokens)
Candidate = tuple[str, Box]
ScoredCandidate = tuple[str, Box, float]


def _model_dir(name: str) -> Path:
    return _MODELS_ROOT / "official_models" / name


def _is_present(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def _line_height(box: Box) -> int:
    return box[3] - box[1]


def _boxes_adjacent(box_a: Box, box_b: Box) -> bool:
    """True if two [x_min, y_min, x_max, y_max] line boxes are close enough (small vertical
    gap relative to line height, overlapping horizontal range) to belong to the same block."""
    avg_height = (_line_height(box_a) + _line_height(box_b)) / 2
    vertical_gap = max(box_b[1] - box_a[3], box_a[1] - box_b[3])
    horizontal_overlap = min(box_a[2], box_b[2]) - max(box_a[0], box_b[0])
    return vertical_gap < avg_height and horizontal_overlap > 0


def _box_center(box: Box) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def _proportional_tokens(words: list[str], line_box: Box) -> list[Token]:
    """Split a line's box into one box per real (non-whitespace) word, proportionally to each
    word's share of the line's total character count - PaddleOCR's own per-word boxes can be
    badly wrong for isolated accented letters, so geometry is derived only from the line's own
    (reliable) box. Each token also records whether a real space preceded it, so windows can be
    rejoined without inserting one where the source text had none."""
    total_len = sum(len(word) for word in words)
    if total_len == 0:
        return []

    x_min, y_min, x_max, y_max = line_box
    width = x_max - x_min

    tokens: list[Token] = []
    offset = 0
    had_space = False
    for word in words:
        length = len(word)
        if word.strip():
            start = x_min + round(width * offset / total_len)
            end = x_min + round(width * (offset + length) / total_len)
            tokens.append((word, (start, y_min, end, y_max), had_space))
            had_space = False
        else:
            had_space = True
        offset += length

    return tokens


def _consistent_size(
    needle_box: Box,
    box: Box,
    width_tolerance: float = 0.3,
    width_min_slack: float = 12,
    height_tolerance: float = 0.6,
    height_min_slack: float = 18,
) -> bool:
    """True if `box`'s size is close enough to `needle_box`'s. Since the text already matched
    by this point, a large mismatch here means the same text is rendered at a different scale -
    out of scope by design, so the candidate is dropped rather than kept with a wrongly-sized
    box. Width and height use different tolerances: width tracks font size reliably, but height
    varies by up to ~50% between otherwise-identical detections, so it's only a loose backstop."""
    needle_w, needle_h = needle_box[2] - needle_box[0], needle_box[3] - needle_box[1]
    box_w, box_h = box[2] - box[0], box[3] - box[1]
    if needle_w <= 0 or needle_h <= 0:
        return False
    slack_w = max(width_tolerance * needle_w, width_min_slack)
    slack_h = max(height_tolerance * needle_h, height_min_slack)
    return abs(box_w - needle_w) <= slack_w and abs(box_h - needle_h) <= slack_h


def _union_box(boxes: list[Box]) -> Box:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _cluster_lines(lines: list[Line]) -> list[list[Line]]:
    """Group OCR lines into connected components of geometrically-adjacent lines."""
    parent = list(range(len(lines)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            if _boxes_adjacent(lines[i][1], lines[j][1]):
                parent[find(i)] = find(j)

    groups: dict[int, list[Line]] = {}
    for i, line in enumerate(lines):
        groups.setdefault(find(i), []).append(line)

    return list(groups.values())


def _join(lines: list[Line]) -> tuple[str, Box]:
    ordered = sorted(lines, key=lambda line: line[1][1])
    text = " ".join(line[0] for line in ordered)
    box = _union_box([line[1] for line in ordered])
    return text, box


def _windows(
    items: list[Any],
    text_of: Callable[[Any], str],
    box_of: Callable[[Any], Box],
    sep_of: Callable[[Any], str] = lambda item: " ",
) -> list[Candidate]:
    """Every contiguous sub-sequence of an ordered list of items, as a (joined text, union box)
    candidate - includes the full sequence and every partial run, down to single items.
    `sep_of(item)` gives the separator to insert before `item` (when not first in the group)."""
    candidates: list[Candidate] = []
    for i in range(len(items)):
        for j in range(i, len(items)):
            group = items[i : j + 1]
            parts: list[str] = []
            for k, item in enumerate(group):
                if k > 0:
                    parts.append(sep_of(item))
                parts.append(text_of(item))
            candidates.append(("".join(parts), _union_box([box_of(item) for item in group])))
    return candidates


def _iou(box_a: Box, box_b: Box) -> float:
    x1, y1 = max(box_a[0], box_b[0]), max(box_a[1], box_b[1])
    x2, y2 = min(box_a[2], box_b[2]), min(box_a[3], box_b[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    if intersection == 0:
        return 0.0
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    return intersection / (area_a + area_b - intersection)


def _suppress_overlaps(candidates: list[ScoredCandidate], iou_threshold: float = 0.1) -> list[ScoredCandidate]:
    """Keep the best-scoring candidate per overlapping group. Word/line windows routinely
    produce several near-identical boxes for the same real match (e.g. a line's full-word
    window vs its own detection box) - this collapses them to one, keeping the best score."""
    kept: list[ScoredCandidate] = []
    for text, box, similarity in sorted(candidates, key=lambda c: c[2], reverse=True):
        if any(_iou(box, kept_box) > iou_threshold for _, kept_box, _ in kept):
            continue
        kept.append((text, box, similarity))
    return kept


def _block_candidates(lines: list[Line]) -> list[Candidate]:
    """Build haystack candidates at two granularities: word windows within a line (so a needle
    matching only part of a longer line still matches, tightly boxed), and line windows within
    an adjacency cluster (so a needle spanning a few stacked lines matches just those, not a
    bigger surrounding block)."""
    # Line windows first: on a similarity tie, _suppress_overlaps keeps whichever came first,
    # and a line's own detection box is more precise than a word-interpolated one.
    candidates: list[Candidate] = []
    for cluster in _cluster_lines(lines):
        ordered = sorted(cluster, key=lambda line: line[1][1])
        candidates += _windows(ordered, text_of=lambda line: line[0], box_of=lambda line: line[1])

    for _, _, _, tokens in lines:
        if tokens:
            candidates += _windows(
                tokens,
                text_of=lambda t: t[0],
                box_of=lambda t: t[1],
                sep_of=lambda t: " " if t[2] else "",
            )

    return list(dict.fromkeys(candidates))


class Ocr(Detector):
    """
    This class implements an image detection algorithm based on OCR (Optical Character Recognition).
    It also provides methods to locate a given text in an image or returns all text data in an image.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

        self._cache: dict[OcrFidelity, PaddleOCR] = {}

    def _get_engine(self, fidelity: OcrFidelity) -> PaddleOCR:
        if fidelity in self._cache:
            return self._cache[fidelity]

        detection, recognition = _PADDLE_MODELS[fidelity]
        det_dir, rec_dir = _model_dir(detection), _model_dir(recognition)

        common = {
            "text_detection_model_name": detection,
            "text_recognition_model_name": recognition,
            "return_word_box": True,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            # The oneDNN/PIR CPU backend fails on PP-OCRv6 models with a
            # "ConvertPirAttribute2RuntimeAttribute not support" error on this paddlepaddle
            # build; the plain CPU backend runs the same models correctly.
            "enable_mkldnn": False,
        }

        # The model name is required even when a local dir is given (used to validate the dir's
        # own config), so it's always passed - only the *_dir overrides change based on presence.
        if _is_present(det_dir) and _is_present(rec_dir):
            ocr = PaddleOCR(text_detection_model_dir=str(det_dir), text_recognition_model_dir=str(rec_dir), **common)
        else:
            try:
                ocr = PaddleOCR(**common)
            except Exception as e:
                raise RuntimeError(
                    f"PaddleOCR models for fidelity {fidelity.name} are not available locally "
                    f"({det_dir}, {rec_dir}) and could not be downloaded: {e}. Connect to the network "
                    "once to fetch them, or place the model files there manually."
                ) from e

        self._cache[fidelity] = ocr
        return ocr

    def _readtext(self, image: np.ndarray, fidelity: OcrFidelity) -> list[Line]:
        """
        Run OCR on a BGR image and return line-level results, each with a word-level breakdown
        (see `_proportional_tokens`) so partial-line matches can be found precisely.

        :param image: BGR image (cv2 format)
        :param fidelity: Model profile to use
        :return: List of (text, box(x_min, y_min, x_max, y_max), score, tokens)
            where tokens is a list of (word_text, word_box, had_space_before)
        """
        engine = self._get_engine(fidelity)

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result = engine.predict(rgb)

        if not result:
            return []

        page = result[0]
        lines: list[Line] = []
        for text, box, score, words in zip(page["rec_texts"], page["rec_boxes"], page["rec_scores"], page["text_word"]):
            x_min, y_min, x_max, y_max = (int(v) for v in box)
            line_box: Box = (x_min, y_min, x_max, y_max)
            lines.append((text, line_box, float(score), _proportional_tokens(words, line_box)))
        return lines

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """
        Normalized, case-insensitive similarity between two strings in [0, 1].

        :param a: First string
        :param b: Second string
        :return: Similarity ratio
        """
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def compute(
        self, needle: np.ndarray, haystack: np.ndarray, target: tuple[int, int], params: Optional[dict]
    ) -> list[list]:
        params = params or {}
        fidelity = params.get("fidelity", OcrFidelity.FAST)
        threshold = params.get("confidence_threshold", 0.8)

        needle_lines = self._readtext(needle, fidelity)
        if not needle_lines:
            return []

        needle_text, needle_box = _join(needle_lines)
        needle_h, needle_w = needle.shape[:2]
        needle_center = _box_center(needle_box)
        self.logger.debug("needle text=%r box=%s (size=%dx%d)", needle_text, needle_box, needle_w, needle_h)

        scored: list[ScoredCandidate] = []
        for text, box in _block_candidates(self._readtext(haystack, fidelity)):
            similarity = self._similarity(needle_text, text)
            passes_similarity = similarity >= threshold
            passes_size = _consistent_size(needle_box, box)
            if passes_similarity and passes_size:
                scored.append((text, box, similarity))
            if passes_similarity or similarity >= threshold * 0.7:
                self.logger.debug(
                    "candidate text=%r box=%s similarity=%.3f passes_similarity=%s passes_size=%s",
                    text,
                    box,
                    similarity,
                    passes_similarity,
                    passes_size,
                )

        matches = []
        for _, box, similarity in _suppress_overlaps(scored):
            # Translate the needle's full rectangle (not just its text box), anchored on box
            # *centers* rather than corners - a corner is sensitive to which single line is
            # leftmost/topmost in a multi-line box, while the center is stable across two
            # independent detections.
            box_center = _box_center(box)
            dx, dy = box_center[0] - needle_center[0], box_center[1] - needle_center[1]
            corners = [
                (dx, dy),
                (needle_w + dx, dy),
                (needle_w + dx, needle_h + dy),
                (dx, needle_h + dy),
            ]
            projected_target = (target[0] + dx, target[1] + dy)
            self.logger.debug(
                "kept match box=%s similarity=%.3f dx=%.1f dy=%.1f -> corners=%s target=%s",
                box,
                similarity,
                dx,
                dy,
                corners,
                projected_target,
            )

            matches.append([corners, projected_target, similarity])

        return matches

    def read_text_on_image(
        self,
        image: np.ndarray,
        fidelity: OcrFidelity,
        area: Optional[tuple[int, int, int, int]] = None,
    ) -> str:
        """
        Read all text visible in an image (or a sub-area of it).

        :param image: BGR image (cv2 format)
        :param fidelity: Model profile to use - required, callers must pick one explicitly
        :param area: (top_left_x, top_left_y, width, height) to restrict the read to, defaults to the whole image
        :return: Detected text, one OCR line per line, top-to-bottom, joined by "\\n" - empty string if none found
        """
        if area:
            x, y, w, h = area
            image = image[y : y + h, x : x + w]

        lines = self._readtext(image, fidelity)
        ordered = sorted(lines, key=lambda line: line[1][1])
        return "\n".join(line[0] for line in ordered)

    def locate_text_on_image(
        self,
        image: np.ndarray,
        text: str,
        fidelity: OcrFidelity,
        confidence_threshold: float,
        area: Optional[tuple[int, int, int, int]] = None,
    ) -> list[Match]:
        """
        Locate every occurrence of `text` in an image (or a sub-area of it).

        Unlike compute(), there is no needle image here, so there is nothing to size-check a
        candidate against - a match is accepted at whatever size the text actually is. There is
        also no needle-relative offset to preserve, so `target` is simply the matched box's
        center - matching how Detector.locate() itself defaults a needle's own target.

        :param image: BGR image (cv2 format)
        :param text: Text to search for
        :param fidelity: Model profile to use - required, callers must pick one explicitly
        :param confidence_threshold: Minimum similarity (0-1) to accept a match - required
        :param area: (top_left_x, top_left_y, width, height) to restrict the search to, defaults to the whole image
        :return: List of Match(box, target, confidence), in the original image's coordinates
        """
        if area:
            x, y, w, h = area
            image = image[y : y + h, x : x + w]

        scored: list[ScoredCandidate] = []
        for candidate_text, box in _block_candidates(self._readtext(image, fidelity)):
            similarity = self._similarity(text, candidate_text)
            if similarity >= confidence_threshold:
                scored.append((candidate_text, box, similarity))

        raw_matches = []
        for _, box, similarity in _suppress_overlaps(scored):
            x_min, y_min, x_max, y_max = box
            corners = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
            center = ((x_min + x_max) // 2, (y_min + y_max) // 2)
            raw_matches.append([corners, center, similarity])

        return self.format(raw_matches, (area[0], area[1]) if area else (0, 0))
