import time

import pytest

import guimauve.controller as controller_module
from guimauve.detection.detector import Match, Point
from guimauve.enums import MatchSort, OcrFidelity, ScreenArea
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, Target, TextVariant


class FakeOcr:
    """Stands in for the Ocr class the controller instantiates for text variants."""

    calls: list[tuple] = []
    matches: list[Match] = []

    def locate_text_on_image(self, image, text, fidelity, confidence_threshold, area=None):
        FakeOcr.calls.append((text, fidelity, confidence_threshold, area))
        return list(FakeOcr.matches)

    def read_text_on_image(self, image, fidelity):
        FakeOcr.calls.append((image.shape, fidelity))
        return "text"

    @staticmethod
    def sort(matches, order_by):
        FakeOcr.calls.append(("sort", order_by))
        return matches


@pytest.fixture
def ocr(monkeypatch):
    monkeypatch.setattr(controller_module, "Ocr", FakeOcr)
    monkeypatch.setattr(FakeOcr, "calls", [])
    monkeypatch.setattr(FakeOcr, "matches", [])
    return FakeOcr


def match(x, y, confidence=1.0) -> Match:
    return Match(box=None, target=Point(x, y), confidence=confidence)


def image(path, name="image", timeout=0.05, element=None, **variant) -> Element:
    return Element(
        name=name, timeout=timeout, variants=[ImageVariant(name="variant", path=path, **variant)], **(element or {})
    )


# --- coordinates ---


def test_locate_without_element_returns_nothing(controller):
    assert controller.locate() == []


def test_locate_coordinates(controller, detectors):
    [found] = controller.locate(element=Element(name="point", x=10, y=20))
    assert found == Match(box=None, target=Point(10, 20), confidence=1.0)
    assert not any(fake.calls for fake in detectors.values())


def test_locate_relative_coordinates_from_mouse(controller, fake_driver):
    fake_driver.position = (50, 50)
    [found] = controller.locate(element=Element(name="point", rel_x=10, rel_y=-5))
    assert found.target == (60, 45)


# --- image variants: what the controller hands to the detectors ---


def test_locate_image_searches_the_screen_with_the_template_detector(
    controller, detectors, needle, needle_path, fake_driver
):
    detectors["template"].matches = [match(1, 2)]
    assert controller.locate(element=image(needle_path)) == [match(1, 2)]

    [call] = detectors["template"].calls
    assert call["needle"].shape == needle.shape
    assert call["haystack"].shape == fake_driver.screen.shape
    assert call["target"] is None
    assert call["area"] == (0, 0, 1920, 1080)
    assert call["match_sort"] is MatchSort.XY_POSITION
    assert call["limit"] == -1


def test_locate_image_passes_only_its_detector_parameters(controller, detectors, needle_path):
    controller.locate(element=image(needle_path, template_confidence_threshold=0.5))
    params = detectors["template"].calls[0]["params"]
    assert params["confidence_threshold"] == 0.5
    assert params["grayscale"] is True
    assert not any(key.startswith(("template_", "feature_", "ocr_")) for key in params)


def test_locate_image_passes_default_target(controller, detectors, needle_path):
    controller.locate(element=image(needle_path, targets=[Target(name="corner", x=5, y=7)], default_target="corner"))
    assert detectors["template"].calls[0]["target"] == [5, 7]


def test_locate_image_passes_element_target_by_name(controller, detectors, needle_path):
    element = image(
        needle_path,
        targets=[Target(name="a", x=1, y=1), Target(name="b", x=5, y=7)],
        default_target="a",
        element={"target": "b"},
    )
    controller.locate(element=element)
    assert detectors["template"].calls[0]["target"] == [5, 7]


def test_locate_image_passes_element_target_as_coordinates(controller, detectors, needle_path):
    controller.locate(element=image(needle_path, element={"target": [3, 4]}))
    assert detectors["template"].calls[0]["target"] == [3, 4]


def test_locate_image_crops_needle_and_shifts_target_with_match_area(controller, detectors, needle_path):
    element = image(
        needle_path,
        targets=[Target(name="inside", x=20, y=15)],
        default_target="inside",
        match_area=Area(left=10, top=10, right=50, bottom=35),
    )
    controller.locate(element=element)
    call = detectors["template"].calls[0]
    assert call["needle"].shape[:2] == (25, 40)
    assert call["target"] == [10, 5]


def test_locate_with_match_area_is_stable_across_calls(controller, detectors, needle_path):
    element = image(
        needle_path,
        targets=[Target(name="inside", x=20, y=15)],
        default_target="inside",
        match_area=Area(left=10, top=10, right=50, bottom=35),
    )
    controller.locate(element=element)
    controller.locate(element=element)
    assert [call["target"] for call in detectors["template"].calls] == [[10, 5], [10, 5]]


def test_locate_element_does_not_shift_target(controller, detectors, needle_path):
    element = controller._update(
        image(
            needle_path,
            targets=[Target(name="inside", x=20, y=15)],
            default_target="inside",
            match_area=Area(left=10, top=10, right=50, bottom=35),
        )
    )
    controller._locate_element(element)
    controller._locate_element(element)
    assert [call["target"] for call in detectors["template"].calls] == [[10, 5], [10, 5]]


@pytest.mark.parametrize(
    ("search_area", "expected"),
    [(ScreenArea.TOP_LEFT, (0, 0, 960, 540)), (Area(left=10, top=20, right=110, bottom=70), (10, 20, 100, 50))],
)
def test_locate_image_passes_search_area_as_xywh(controller, detectors, needle_path, search_area, expected):
    controller.locate(element=image(needle_path, search_area=search_area))
    assert detectors["template"].calls[0]["area"] == expected


def test_locate_image_rejects_search_area_beyond_screen(controller, detectors, needle_path):
    with pytest.raises(ValueError, match="exceeds the screen size"):
        controller.locate(element=image(needle_path, search_area=Area(left=0, top=0, right=2560, bottom=1440)))
    assert not detectors["template"].calls


def test_locate_image_skips_disabled_detectors(controller, detectors, needle_path):
    controller.locate(element=image(needle_path, use_template=False, use_feature=True))
    assert not detectors["template"].calls
    assert len(detectors["feature"].calls) == 1


def test_locate_image_falls_back_to_next_detector(controller, detectors, needle_path):
    detectors["feature"].matches = [match(1, 2)]
    assert controller.locate(element=image(needle_path, use_feature=True, use_ocr=True)) == [match(1, 2)]
    assert [len(detectors[name].calls) for name in ("template", "feature", "ocr")] == [1, 1, 0]


# --- several variants ---


def test_locate_stops_at_first_variant_found(controller, detectors, needle_path):
    detectors["template"].matches = [match(1, 2)]
    element = Element(
        name="image",
        variants=[ImageVariant(name="first", path=needle_path), ImageVariant(name="second", path=needle_path)],
    )
    controller.locate(element=element)
    assert len(detectors["template"].calls) == 1


@pytest.mark.parametrize(
    ("match_sort", "expected"),
    [
        (MatchSort.XY_POSITION, [match(1, 1, 0.5), match(1, 1, 0.5), match(5, 5, 0.9), match(5, 5, 0.9)]),
        (MatchSort.CONFIDENCE, [match(5, 5, 0.9), match(5, 5, 0.9), match(1, 1, 0.5), match(1, 1, 0.5)]),
    ],
)
def test_locate_find_all_merges_and_sorts_variants(controller, detectors, needle_path, match_sort, expected):
    detectors["template"].matches = [match(5, 5, 0.9), match(1, 1, 0.5)]
    element = Element(
        name="image",
        find_all=True,
        match_sort=match_sort,
        variants=[ImageVariant(name="first", path=needle_path), ImageVariant(name="second", path=needle_path)],
    )
    assert controller.locate(element=element) == expected
    assert len(detectors["template"].calls) == 2


# --- text variants ---


def test_locate_text_variant_uses_ocr(controller, ocr):
    ocr.matches = [match(1, 2)]
    element = Element(name="text", variants=[TextVariant(name="variant", text="OK", search_area=ScreenArea.LEFT)])
    assert controller.locate(element=element) == [match(1, 2)]
    assert ocr.calls == [("OK", OcrFidelity.FAST, 0.8, (0, 0, 960, 1080)), ("sort", MatchSort.XY_POSITION)]


def test_read_text_reads_the_given_screen_area(controller, ocr):
    assert controller.read_text(screen_area=Area(left=10, top=20, right=110, bottom=70)) == "text"
    assert ocr.calls == [((50, 100, 3), OcrFidelity.ACCURATE)]


def test_locate_text_searches_the_given_screen_area(controller, ocr):
    ocr.matches = [match(1, 2)]
    assert controller.locate_text("OK", screen_area=ScreenArea.TOP) == [match(1, 2)]
    assert ocr.calls == [("OK", OcrFidelity.FAST, 0.8, (0, 0, 1920, 540))]


# --- wait ---


def test_wait_on_visible_element(controller, detectors, needle_path):
    detectors["template"].matches = [match(1, 2)]
    result = controller.wait(on=image(needle_path))
    assert result
    assert result.get("image").match == match(1, 2)


def test_wait_off_absent_element(controller, needle_path, detectors):
    result = controller.wait(off=image(needle_path))
    assert result
    assert result.get("image").match is None


def test_wait_on_absent_element_times_out_after_element_timeout(controller, detectors, needle_path):
    start = time.perf_counter()
    result = controller.wait(on=image(needle_path, timeout=0.1))
    assert not result
    assert not result.get("image").success
    assert 0.1 <= time.perf_counter() - start < 1


def test_wait_pauses_between_unsuccessful_polls(controller, detectors, needle_path, sleeps):
    controller.wait(on=image(needle_path))
    assert sleeps
    assert all(0 < delay <= controller_module.POLL_INTERVAL for delay in sleeps)


def test_wait_does_not_pause_when_found_at_first_poll(controller, detectors, needle_path, sleeps):
    detectors["template"].matches = [match(1, 2)]
    controller.wait(on=image(needle_path))
    assert sleeps == []


def test_wait_off_visible_element_times_out(controller, detectors, needle_path):
    detectors["template"].matches = [match(1, 2)]
    assert not controller.wait(off=image(needle_path))


def test_wait_succeeds_only_if_every_element_does(controller, detectors, needle_path):
    detectors["template"].matches = [match(1, 2)]
    result = controller.wait(
        on=[image(needle_path), Element(name="point", x=1, y=1)], off=[image(needle_path, name="gone")]
    )
    assert not result
    assert result.get("image").success
    assert result.get("point").success
    assert not result.get("gone").success


@pytest.mark.parametrize(
    "kwargs",
    [
        {"on": [Element(name="point", x=1, y=1), Element(name="point", x=2, y=2)]},
        {"on": Element(name="point", x=1, y=1), "off": Element(name="point", x=2, y=2)},
    ],
)
def test_wait_rejects_duplicate_names(controller, kwargs):
    with pytest.raises(ValueError, match="same name: point"):
        controller.wait(**kwargs)


def test_wait_accepts_renamed_duplicates(controller):
    point = Element(name="point", x=1, y=1)
    assert controller.wait(on=[point, point(name="other", x=2)])


def test_wait_returns_match_at_match_index(controller, detectors, needle_path):
    detectors["template"].matches = [match(1, 1), match(2, 2)]
    assert controller.wait(on=image(needle_path, element={"match_index": 1})).get("image").match == match(2, 2)


def test_wait_match_index_out_of_range_raises(controller):
    with pytest.raises(Exception, match="Cannot reach match index"):
        controller.wait(on=Element(name="point", x=1, y=1, match_index=1))
