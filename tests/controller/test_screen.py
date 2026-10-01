from types import SimpleNamespace

import cv2 as cv
import numpy as np
import pytest

from guimauve.detection.detector import Match, Point
from guimauve.enums import ScreenArea
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant


@pytest.fixture
def screen(fake_driver):
    """Paints a distinct, colored screen so crops and color order can be checked."""
    height, width = fake_driver.screen.shape[:2]
    fake_driver.screen = np.random.default_rng(0).integers(0, 255, (height, width, 3), dtype=np.uint8)
    return fake_driver.screen


def test_screen_size(controller):
    assert controller.screen_size == (1920, 1080)


def test_screenshot_returns_whole_screen(controller, screen):
    assert np.array_equal(controller.screenshot(), screen)


def test_screenshot_crops_to_area(controller, screen):
    shot = controller.screenshot(screen_area=Area(left=10, top=20, right=110, bottom=70))
    assert np.array_equal(shot, screen[20:70, 10:110])


def test_screenshot_crops_to_screen_area(controller, screen):
    assert np.array_equal(controller.screenshot(screen_area=ScreenArea.BOTTOM_RIGHT), screen[540:, 960:])


def test_screenshot_rejects_area_beyond_screen(controller, screen):
    with pytest.raises(ValueError, match="exceeds the screen size 1920x1080"):
        controller.screenshot(screen_area=Area(left=0, top=0, right=2560, bottom=1440))


def test_screenshot_saves_to_path(controller, screen, tmp_path):
    path = tmp_path / "shot.png"
    controller.screenshot(path=path)
    assert path.is_file()


def test_screenshot_saves_colors_unchanged(controller, screen, tmp_path):
    path = tmp_path / "shot.png"
    controller.screenshot(path=path)
    assert np.array_equal(cv.cvtColor(cv.imread(str(path)), cv.COLOR_BGR2RGB), screen)


# --- scroll_until ---


@pytest.fixture
def scrollable(fake_driver, detectors):
    """Makes each scroll change the screen, and the element appear after `scrollable.until` scrolls."""
    scrollable = SimpleNamespace(until=None, scrolls=0)

    def scroll(v, h):
        fake_driver.calls.append(("mouse_scroll", v, h))
        scrollable.scrolls += 1
        fake_driver.screen = np.full_like(fake_driver.screen, scrollable.scrolls)
        if scrollable.scrolls == scrollable.until:
            detectors["template"].matches = [Match(box=None, target=Point(1, 2), confidence=1.0)]

    fake_driver.mouse_scroll = scroll
    return scrollable


def element(path) -> Element:
    return Element(name="image", variants=[ImageVariant(name="variant", path=path)])


def test_scroll_until_stops_when_screen_no_longer_changes(controller, inputs, detectors, needle_path):
    assert controller.scroll_until(v=-3, element=element(needle_path)) is None
    assert inputs() == [("mouse_scroll", -3, 0)]


def test_scroll_until_does_not_scroll_if_element_is_visible(controller, inputs, detectors, needle_path):
    detectors["template"].matches = [Match(box=None, target=Point(1, 2), confidence=1.0)]
    assert controller.scroll_until(v=-3, element=element(needle_path)).target == (1, 2)
    assert inputs() == []


def test_scroll_until_scrolls_until_element_appears(controller, inputs, scrollable, needle_path):
    scrollable.until = 3
    assert controller.scroll_until(v=-3, element=element(needle_path)).target == (1, 2)
    assert inputs() == [("mouse_scroll", -3, 0)] * 3


def test_scroll_until_stops_at_timeout(controller, scrollable, needle_path):
    assert controller.scroll_until(v=-3, element=element(needle_path), timeout=0.05) is None
    assert scrollable.scrolls > 0
