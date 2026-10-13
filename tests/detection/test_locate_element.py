import numpy as np
import pytest

from guimauve.detection.detector import Box, Match, Point
from guimauve.detection.locate import VariantStatus, locate_element, locate_text, locate_variant
from guimauve.drivers.driver import Screen
from guimauve.enums import MatchSort, OcrFidelity, ScreenArea
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters
from guimauve.models.variant import ImageVariant, Target, TextVariant

MOUSE = (0, 0)


@pytest.fixture
def screen():
    return np.zeros((1080, 1920, 3), dtype=np.uint8)


def grab(image):
    """Capture function returning the same image for any screen."""
    return lambda screen: image


def no_capture(screen):
    raise AssertionError("no capture expected")


def match(x, y, confidence=1.0) -> Match:
    return Match(box=None, target=Point(x, y), confidence=confidence)


def resolve(element: Element) -> Element:
    """Merges default and element values into the element and its variants, as the controller does."""
    element = element.update(Parameters().default, overwrite=False)
    element.variants = [
        variant.update(element, exclude={"name"}, overwrite=False) for variant in element.variants or []
    ]
    return element


def image(path, name="image", element=None, **variant) -> Element:
    return resolve(Element(name=name, variants=[ImageVariant(name="variant", path=path, **variant)], **(element or {})))


def two_images(path, **element) -> Element:
    return resolve(
        Element(
            name="image",
            variants=[ImageVariant(name="first", path=path), ImageVariant(name="second", path=path)],
            **element,
        )
    )


# --- fixed position ---


def test_fixed_position_returns_the_point_without_searching(detectors):
    report = locate_element(resolve(Element(name="point", x=10, y=20)), no_capture, [], MOUSE)
    assert report.matches == [match(10, 20)]
    assert report.fixed_position
    assert report.variants == []
    assert not any(fake.calls for fake in detectors.values())


def test_relative_position_starts_from_the_mouse():
    report = locate_element(resolve(Element(name="point", rel_x=10, rel_y=-5)), no_capture, [], (50, 50))
    assert report.matches[0].target == (60, 45)


# --- image variants: what is handed to the detectors ---


def test_image_is_searched_on_the_screen_with_the_template_detector(detectors, needle, needle_path, screen):
    detectors["template"].matches = [match(1, 2)]
    assert locate_element(image(needle_path), grab(screen), [], MOUSE).matches == [match(1, 2)]

    [call] = detectors["template"].calls
    assert call["needle"].shape == needle.shape
    assert call["haystack"].shape == screen.shape
    assert call["target"] is None
    assert call["area"] == (0, 0, 1920, 1080)
    assert call["match_sort"] is MatchSort.XY_POSITION
    assert call["limit"] == -1


def test_only_the_detector_parameters_are_passed(detectors, needle_path, screen):
    locate_element(image(needle_path, template_confidence_threshold=0.5), grab(screen), [], MOUSE)
    params = detectors["template"].calls[0]["params"]
    assert params["confidence_threshold"] == 0.5
    assert params["grayscale"] is True
    assert not any(key.startswith(("template_", "feature_", "ocr_")) for key in params)


def test_default_target_is_used(detectors, needle_path, screen):
    element = image(needle_path, targets=[Target(name="corner", x=5, y=7)], default_target="corner")
    locate_element(element, grab(screen), [], MOUSE)
    assert detectors["template"].calls[0]["target"] == [5, 7]


def test_element_target_is_used_by_name(detectors, needle_path, screen):
    element = image(
        needle_path,
        targets=[Target(name="a", x=1, y=1), Target(name="b", x=5, y=7)],
        default_target="a",
        element={"target": "b"},
    )
    locate_element(element, grab(screen), [], MOUSE)
    assert detectors["template"].calls[0]["target"] == [5, 7]


def test_element_target_is_used_as_coordinates(detectors, needle_path, screen):
    locate_element(image(needle_path, element={"target": [3, 4]}), grab(screen), [], MOUSE)
    assert detectors["template"].calls[0]["target"] == [3, 4]


def test_unknown_target_name_falls_back_to_the_centre(detectors, needle_path, screen):
    variant = image(needle_path, targets=[Target(name="a", x=1, y=1)]).variants[0]
    locate_variant(variant, screen, "missing")
    assert detectors["template"].calls[0]["target"] is None


def test_match_area_crops_the_needle_and_shifts_the_target(detectors, needle_path, screen):
    element = image(
        needle_path,
        targets=[Target(name="inside", x=20, y=15)],
        default_target="inside",
        match_area=Area(left=10, top=10, right=50, bottom=35),
    )
    locate_element(element, grab(screen), [], MOUSE)
    call = detectors["template"].calls[0]
    assert call["needle"].shape[:2] == (25, 40)
    assert call["target"] == [10, 5]


def test_match_area_does_not_change_the_variant_across_calls(detectors, needle_path, screen):
    element = image(
        needle_path,
        targets=[Target(name="inside", x=20, y=15)],
        default_target="inside",
        match_area=Area(left=10, top=10, right=50, bottom=35),
    )
    locate_element(element, grab(screen), [], MOUSE)
    locate_element(element, grab(screen), [], MOUSE)
    assert [call["target"] for call in detectors["template"].calls] == [[10, 5], [10, 5]]
    assert element.variants[0].targets[0] == Target(name="inside", x=20, y=15)


@pytest.mark.parametrize(
    ("search_area", "expected"),
    [(ScreenArea.TOP_LEFT, (0, 0, 960, 540)), (Area(left=10, top=20, right=110, bottom=70), (10, 20, 100, 50))],
)
def test_search_area_is_passed_as_xywh(detectors, needle_path, screen, search_area, expected):
    locate_element(image(needle_path, search_area=search_area), grab(screen), [], MOUSE)
    assert detectors["template"].calls[0]["area"] == expected


def test_search_area_beyond_the_screen_is_rejected(detectors, needle_path, screen):
    with pytest.raises(ValueError, match="exceeds screen 1: 1920x1080"):
        locate_element(
            image(needle_path, search_area=Area(left=0, top=0, right=2560, bottom=1440)), grab(screen), [], MOUSE
        )
    assert not detectors["template"].calls


def test_disabled_detectors_are_skipped(detectors, needle_path, screen):
    locate_element(image(needle_path, use_template=False, use_feature=True), grab(screen), [], MOUSE)
    assert not detectors["template"].calls
    assert len(detectors["feature"].calls) == 1


def test_next_detector_is_tried_and_reported_when_the_first_finds_nothing(detectors, needle_path, screen):
    detectors["feature"].matches = [match(1, 2)]
    report = locate_element(image(needle_path, use_feature=True, use_ocr=True), grab(screen), [], MOUSE)
    assert report.matches == [match(1, 2)]
    assert report.variants[0].method == "feature"
    assert [len(detectors[name].calls) for name in ("template", "feature", "ocr")] == [1, 1, 0]


# --- reports and several variants ---


def test_variant_not_found_is_reported(detectors, needle_path, screen):
    report = locate_element(image(needle_path), grab(screen), [], MOUSE)
    assert not report.found
    assert [v.status for v in report.variants] == [VariantStatus.NOT_FOUND]
    assert report.variants[0].method is None


def test_search_stops_at_the_first_variant_found_and_skips_the_others(detectors, needle_path, screen):
    detectors["template"].matches = [match(1, 2)]
    report = locate_element(two_images(needle_path), grab(screen), [], MOUSE)
    assert report.found
    assert [v.status for v in report.variants] == [VariantStatus.FOUND, VariantStatus.SKIPPED]
    assert [v.variant.name for v in report.variants] == ["first", "second"]
    assert report.variants[0].method == "template"
    assert len(detectors["template"].calls) == 1


@pytest.mark.parametrize(
    ("match_sort", "expected"),
    [
        (MatchSort.XY_POSITION, [match(1, 1, 0.5), match(1, 1, 0.5), match(5, 5, 0.9), match(5, 5, 0.9)]),
        (MatchSort.CONFIDENCE, [match(5, 5, 0.9), match(5, 5, 0.9), match(1, 1, 0.5), match(1, 1, 0.5)]),
    ],
)
def test_find_all_searches_every_variant_and_sorts_matches(detectors, needle_path, screen, match_sort, expected):
    detectors["template"].matches = [match(5, 5, 0.9), match(1, 1, 0.5)]
    report = locate_element(two_images(needle_path, find_all=True, match_sort=match_sort), grab(screen), [], MOUSE)
    assert report.matches == expected
    assert [v.status for v in report.variants] == [VariantStatus.FOUND, VariantStatus.FOUND]
    assert len(detectors["template"].calls) == 2


def test_locate_variant_reports_a_single_variant(detectors, needle_path, screen):
    detectors["template"].matches = [match(1, 2)]
    report = locate_variant(image(needle_path).variants[0], screen, None)
    assert report.status is VariantStatus.FOUND
    assert report.method == "template"
    assert report.matches == [match(1, 2)]


# --- text variants ---


def test_text_variant_is_searched_with_ocr(ocr, screen):
    ocr.matches = [match(1, 2)]
    element = resolve(
        Element(name="text", variants=[TextVariant(name="variant", text="OK", search_area=ScreenArea.LEFT)])
    )
    report = locate_element(element, grab(screen), [], MOUSE)
    assert report.matches == [match(1, 2)]
    assert report.variants[0].method == "ocr"
    assert ocr.calls == [("OK", OcrFidelity.FAST, 0.8, (0, 0, 960, 1080)), ("sort", MatchSort.XY_POSITION)]


def test_unresolved_text_variant_is_rejected(ocr, screen):
    with pytest.raises(ValueError, match="must be resolved"):
        locate_variant(TextVariant(name="variant", text="OK"), screen, None)


# --- several screens ---

# Screen 2 (1280x1024) is left of the primary screen (1920x1080); the gap below it is off-screen.
SCREENS = [Screen(-1280, 0, 3200, 1080), Screen(0, 0, 1920, 1080), Screen(-1280, 0, 1280, 1024)]


class Grab:
    """Capture function recording which screens are captured, each one a blank image of its size."""

    def __init__(self):
        self.screens: list[int] = []

    def __call__(self, screen):
        self.screens.append(screen)
        rect = SCREENS[screen]
        return np.zeros((rect.height, rect.width, 3), dtype=np.uint8)


def found_on(detectors, *widths, at=(10, 20)):
    """Makes the template detector find one match only on images of the given widths."""
    calls = detectors["template"].calls

    def locate(needle, haystack, **kwargs):
        calls.append({"needle": needle, "haystack": haystack, **kwargs})
        return [match(*at)] if haystack.shape[1] in widths else []

    detectors["template"].locate = locate


def test_matches_are_moved_to_desktop_coordinates(detectors, needle_path):
    detectors["template"].matches = [
        Match(box=Box(Point(0, 0), Point(9, 0), Point(9, 9), Point(0, 9)), target=Point(10, 20), confidence=1.0)
    ]
    [found] = locate_element(image(needle_path, element={"screen": 2}), Grab(), SCREENS, MOUSE).matches
    assert found.target == (-1270, 20)
    assert found.box == Box(Point(-1280, 0), Point(-1271, 0), Point(-1271, 9), Point(-1280, 9))


def test_each_variant_is_searched_on_every_screen_before_the_next_one(detectors, needle_path):
    found_on(detectors, 1280)
    grab = Grab()
    report = locate_element(two_images(needle_path, screen=[1, 2]), grab, SCREENS, MOUSE)
    assert report.matches == [match(-1270, 20)]
    assert [v.status for v in report.variants] == [VariantStatus.FOUND, VariantStatus.SKIPPED]
    assert [call["haystack"].shape[1] for call in detectors["template"].calls] == [1920, 1280]
    assert grab.screens == [1, 2]


def test_each_screen_is_captured_once(detectors, needle_path):
    grab = Grab()
    report = locate_element(two_images(needle_path, screen=[1, 2]), grab, SCREENS, MOUSE)
    assert not report.found
    assert grab.screens == [1, 2]
    assert len(detectors["template"].calls) == 4


def test_find_all_merges_and_sorts_matches_of_every_screen(detectors, needle_path):
    found_on(detectors, 1920, 1280)
    element = image(needle_path, element={"screen": [1, 2], "find_all": True, "match_sort": MatchSort.XY_POSITION})
    report = locate_element(element, Grab(), SCREENS, MOUSE)
    assert [m.target for m in report.matches] == [(-1270, 20), (10, 20)]


def test_all_screens_drop_matches_in_the_gaps_between_screens(detectors, needle_path):
    detectors["template"].matches = [match(100, 100), match(100, 1050)]
    report = locate_element(image(needle_path, element={"screen": 0}), Grab(), SCREENS, MOUSE)
    assert [m.target for m in report.matches] == [(-1180, 100)]


def test_screen_is_skipped_when_the_image_does_not_fit_in_its_search_area(detectors, needle_path):
    element = image(needle_path, search_area=Area(left=0, top=0, right=30, bottom=30))
    report = locate_element(element, Grab(), SCREENS, MOUSE)
    assert report.variants[0].status is VariantStatus.NOT_FOUND
    assert report.variants[0].unfit_screens == [1]
    assert not detectors["template"].calls


def test_search_area_beyond_a_smaller_screen_is_rejected(detectors, needle_path):
    element = image(needle_path, search_area=Area(left=0, top=0, right=1500, bottom=1000), element={"screen": [1, 2]})
    with pytest.raises(ValueError, match="exceeds screen 2: 1280x1024"):
        locate_element(element, Grab(), SCREENS, MOUSE)


@pytest.mark.parametrize(("screen", "expected"), [(2, (-1270, 20)), ([2, 1], (-1270, 20)), (0, (-1270, 20))])
def test_fixed_position_is_relative_to_the_first_screen_searched(screen, expected):
    element = resolve(Element(name="point", x=10, y=20, screen=screen))
    assert locate_element(element, no_capture, SCREENS, MOUSE).matches[0].target == expected


def test_fixed_position_on_a_missing_screen_is_rejected():
    with pytest.raises(ValueError, match="Screen 5 does not exist: 2 screens available"):
        locate_element(resolve(Element(name="point", x=10, y=20, screen=5)), no_capture, SCREENS, MOUSE)


def test_relative_position_ignores_the_screen():
    element = resolve(Element(name="point", rel_x=10, rel_y=-5, screen=2))
    assert locate_element(element, no_capture, SCREENS, (50, 50)).matches[0].target == (60, 45)


def test_a_driver_without_screens_is_searched_once_at_the_origin(detectors, needle_path, screen):
    detectors["template"].matches = [match(10, 20)]
    captured = []
    report = locate_element(
        image(needle_path, element={"screen": [2, 3]}), lambda n: captured.append(n) or screen, [], MOUSE
    )
    assert report.matches == [match(10, 20)]
    assert captured == [2]


def test_text_is_located_on_each_screen_in_desktop_coordinates(ocr):
    ocr.matches = [match(10, 20)]
    grab = Grab()
    found = locate_text("OK", grab, SCREENS, [1, 2], ScreenArea.LEFT, OcrFidelity.FAST, 0.8)
    assert [m.target for m in found] == [(10, 20), (-1270, 20)]
    assert grab.screens == [1, 2]
    assert [call[3] for call in ocr.calls] == [(0, 0, 960, 1080), (0, 0, 640, 1024)]
