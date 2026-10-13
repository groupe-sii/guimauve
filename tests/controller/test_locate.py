import time

import pytest

import guimauve.controller as controller_module
from guimauve.detection.detector import Match, Point
from guimauve.enums import OcrFidelity, ScreenArea
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant


def match(x, y, confidence=1.0) -> Match:
    return Match(box=None, target=Point(x, y), confidence=confidence)


def image(path, name="image", timeout=0.05, element=None, **variant) -> Element:
    return Element(
        name=name, timeout=timeout, variants=[ImageVariant(name="variant", path=path, **variant)], **(element or {})
    )


# --- coordinates ---


def test_locate_without_element_returns_nothing(controller):
    assert controller.locate() == []


def test_locate_coordinates_does_not_capture_the_screen(controller, detectors, fake_driver):
    [found] = controller.locate(element=Element(name="point", x=10, y=20))
    assert found == Match(box=None, target=Point(10, 20), confidence=1.0)
    assert not any(fake.calls for fake in detectors.values())
    assert not any(call[0] == "capture" for call in fake_driver.calls)


def test_locate_relative_coordinates_from_mouse(controller, fake_driver):
    fake_driver.position = (50, 50)
    [found] = controller.locate(element=Element(name="point", rel_x=10, rel_y=-5))
    assert found.target == (60, 45)


# --- delegation to the detection module ---


def test_locate_resolves_the_element_and_searches_the_captured_screen(controller, detectors, needle_path, fake_driver):
    detectors["template"].matches = [match(1, 2)]
    assert controller.locate(element=image(needle_path)) == [match(1, 2)]

    [call] = detectors["template"].calls
    assert call["haystack"].shape == fake_driver.screen.shape
    assert call["params"]["grayscale"] is True  # default value merged by the controller
    assert ("capture", 1, None) in fake_driver.calls


# --- text ---


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
