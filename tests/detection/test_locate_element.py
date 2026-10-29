"""Order of the matches returned by locate_element, on one or several screens."""

import cv2 as cv
import numpy as np
import pytest

from guimauve.detection.detector import Match, Point
from guimauve.drivers.driver import Screen
from guimauve.enums import MatchSort
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant

# Two screens side by side: screen 2 on the right of the primary one.
SCREENS = [Screen(0, 0, 3840, 1080), Screen(0, 0, 1920, 1080), Screen(1920, 0, 1920, 1080)]


def match(x, y, confidence=1.0) -> Match:
    return Match(box=None, target=Point(x, y), confidence=confidence)


class ScreenDetector:
    """Returns, for a needle and a screen, the matches configured for them, in image coordinates."""

    def __init__(self):
        self.matches: dict[tuple[int, int], list[Match]] = {}  # (needle width, screen) -> matches
        self.sorts: list = []

    def locate(self, needle, haystack, match_sort=None, **_):
        self.sorts.append(match_sort)
        return list(self.matches.get((needle.shape[1], int(haystack[0, 0, 0])), []))


@pytest.fixture
def detector(monkeypatch):
    import guimauve.detection.locate as locate_module  # imported here: it loads the OCR engine

    fake = ScreenDetector()
    monkeypatch.setitem(locate_module.DETECTORS, "template", lambda: fake)
    return fake


@pytest.fixture
def needles(tmp_path):
    """Paths of two needle images told apart by their width: 60 for the first, 50 for the second."""
    paths = []
    for width in (60, 50):
        path = tmp_path / f"needle_{width}.png"
        cv.imwrite(str(path), np.zeros((40, width, 3), dtype=np.uint8))
        paths.append(path)
    return paths


def grab(screen: int) -> np.ndarray:
    """Image of a screen, marked with its number to tell the screens apart."""
    return np.full((200, 200, 3), screen, dtype=np.uint8)


def element(needles, count=1, **settings) -> Element:
    defaults = {"find_all": False, "screen": 1, "match_sort": MatchSort.TOP_LEFT, "target": None}
    variants = [
        ImageVariant(
            name=f"V{index}",
            path=path,
            use_template=True,
            use_feature=False,
            use_ocr=False,
            match_sort=settings.get("match_sort", MatchSort.TOP_LEFT),
        )
        for index, path in enumerate(needles[:count])
    ]
    return Element(name="E", variants=variants, **{**defaults, **settings})


def locate(el: Element) -> list[tuple[int, int]]:
    from guimauve.detection.locate import locate_element

    return [tuple(m.target) for m in locate_element(el, grab, SCREENS, (0, 0)).matches]


# --- one screen ---


@pytest.mark.parametrize(
    ("corner", "expected"),
    [
        # (150, 10) and (10, 150), then (10, 10) and (150, 150), tie: the match nearest the corner horizontally wins
        (MatchSort.TOP_LEFT, [(10, 10), (10, 150), (150, 10), (150, 150)]),
        (MatchSort.TOP_RIGHT, [(150, 10), (150, 150), (10, 10), (10, 150)]),
        (MatchSort.BOTTOM_LEFT, [(10, 150), (10, 10), (150, 150), (150, 10)]),
        (MatchSort.BOTTOM_RIGHT, [(150, 150), (150, 10), (10, 150), (10, 10)]),
    ],
)
def test_matches_are_sorted_from_the_corner(detector, needles, corner, expected):
    detector.matches[60, 1] = [match(150, 150), match(10, 150), match(150, 10), match(10, 10)]
    assert locate(element(needles, match_sort=corner)) == expected


def test_detectors_do_not_sort_matches_of_an_element(detector, needles):
    detector.matches[60, 1] = [match(10, 10)]
    locate(element(needles))
    assert detector.sorts == [None]


def test_without_find_all_the_variant_sort_is_used(detector, needles):
    detector.matches[60, 1] = [match(10, 10), match(150, 150)]
    el = element(needles, match_sort=MatchSort.TOP_LEFT)
    el.variants[0].match_sort = MatchSort.BOTTOM_RIGHT
    assert locate(el) == [(150, 150), (10, 10)]


# --- several screens ---


def test_only_the_given_screen_is_sorted(detector, needles):
    detector.matches[60, 1] = [match(10, 10)]
    detector.matches[60, 2] = [match(150, 150), match(10, 10)]
    assert locate(element(needles, screen=2, find_all=True)) == [(1930, 10), (2070, 150)]


@pytest.mark.parametrize(
    ("screens", "corner", "expected"),
    [
        ([1, 2], MatchSort.TOP_LEFT, [(10, 10), (150, 150), (1930, 10), (2070, 150)]),
        ([2, 1], MatchSort.TOP_LEFT, [(1930, 10), (2070, 150), (10, 10), (150, 150)]),
        ([1, 2], MatchSort.BOTTOM_RIGHT, [(150, 150), (10, 10), (2070, 150), (1930, 10)]),
    ],
)
def test_matches_follow_the_order_of_the_screens_then_the_corner(detector, needles, screens, corner, expected):
    detector.matches[60, 1] = [match(150, 150), match(10, 10)]
    detector.matches[60, 2] = [match(150, 150), match(10, 10)]
    assert locate(element(needles, screen=screens, find_all=True, match_sort=corner)) == expected


def test_matches_of_several_variants_are_grouped_by_screen(detector, needles):
    # variant 0 then variant 1 are searched on each screen; their matches interleave before sorting
    detector.matches[60, 2] = [match(150, 150)]
    detector.matches[60, 1] = [match(150, 150)]
    detector.matches[50, 2] = [match(10, 10)]
    detector.matches[50, 1] = [match(10, 10)]
    el = element(needles, count=2, screen=[2, 1], find_all=True)
    assert locate(el) == [(1930, 10), (2070, 150), (10, 10), (150, 150)]


def test_each_match_keeps_its_screen_and_its_variant(detector, needles):
    from guimauve.detection.locate import locate_element

    detector.matches[60, 2] = [match(150, 150)]
    detector.matches[60, 1] = [match(150, 150)]
    detector.matches[50, 2] = [match(10, 10)]
    detector.matches[50, 1] = [match(10, 10)]
    report = locate_element(element(needles, count=2, screen=[2, 1], find_all=True), grab, SCREENS, (0, 0))

    assert report.match_screens == [2, 2, 1, 1]
    assert report.match_variants == [1, 0, 1, 0]


def test_without_find_all_the_matches_come_from_the_first_variant_found(detector, needles):
    from guimauve.detection.locate import locate_element

    detector.matches[50, 1] = [match(150, 150), match(10, 10)]
    report = locate_element(element(needles, count=2), grab, SCREENS, (0, 0))

    assert (report.match_screens, report.match_variants) == ([1, 1], [1, 1])


def test_a_fixed_position_has_no_screen_nor_variant(needles):
    from guimauve.detection.locate import locate_element

    report = locate_element(element(needles, x=5, y=6), grab, SCREENS, (0, 0))

    assert report.fixed_position
    assert (report.match_screens, report.match_variants) == ([], [])


def test_a_stopped_search_ends_before_its_next_step(detector, needles):
    from guimauve.detection.locate import SearchStoppedError, locate_element

    el = element(needles, count=2, screen=[1, 2], find_all=True)
    with pytest.raises(SearchStoppedError):
        locate_element(el, grab, SCREENS, (0, 0), stopped=lambda: len(detector.sorts) == 1)

    assert len(detector.sorts) == 1  # one detection, on the first screen, then stopped


def test_a_search_never_stopped_ends(detector, needles):
    from guimauve.detection.locate import locate_element

    detector.matches[60, 1] = [match(10, 10)]
    report = locate_element(element(needles), grab, SCREENS, (0, 0), stopped=lambda: False)

    assert report.found


def test_without_find_all_the_first_screen_with_a_match_wins(detector, needles):
    detector.matches[60, 1] = [match(10, 10)]
    detector.matches[60, 2] = [match(150, 150), match(10, 10)]
    assert locate(element(needles, screen=[2, 1])) == [(1930, 10), (2070, 150)]


@pytest.mark.parametrize(
    ("corner", "expected"),
    [
        (MatchSort.TOP_LEFT, [(10, 10), (150, 150), (1930, 10)]),
        (MatchSort.TOP_RIGHT, [(1930, 10), (150, 150), (10, 10)]),
    ],
)
def test_screen_zero_is_sorted_across_the_whole_desktop(detector, needles, corner, expected):
    # on the image of all screens, x = 1930 lies on screen 2
    detector.matches[60, 0] = [match(150, 150), match(1930, 10), match(10, 10)]
    assert locate(element(needles, screen=0, find_all=True, match_sort=corner)) == expected


# Screen 2 on the left of the primary one: its desktop coordinates are negative.
LEFT_SCREENS = [Screen(-1920, 0, 3840, 1080), Screen(0, 0, 1920, 1080), Screen(-1920, 0, 1920, 1080)]


def test_screen_on_the_left_keeps_the_order_of_the_screens_given(detector, needles):
    from guimauve.detection.locate import locate_element

    detector.matches[60, 1] = [match(10, 10)]
    detector.matches[60, 2] = [match(10, 10)]
    el = element(needles, screen=[1, 2], find_all=True)
    found = locate_element(el, grab, LEFT_SCREENS, (0, 0)).matches
    # (-1910, 10) is nearer the top-left corner, but screen 1 is listed first
    assert [tuple(m.target) for m in found] == [(10, 10), (-1910, 10)]


def test_screen_zero_with_a_screen_on_the_left_is_sorted_from_the_desktop_corner(detector, needles):
    from guimauve.detection.locate import locate_element

    # the image of all screens starts at x = -1920: x = 10 lies on screen 2, x = 1930 on the primary screen
    detector.matches[60, 0] = [match(1930, 10), match(10, 10)]
    el = element(needles, screen=0, find_all=True)
    found = locate_element(el, grab, LEFT_SCREENS, (0, 0)).matches
    assert [tuple(m.target) for m in found] == [(-1910, 10), (10, 10)]
