import numpy as np
import pytest

import guimauve.drivers.local.driver as local_module
from guimauve.drivers.driver import Screen
from guimauve.drivers.local.driver import LocalDriver
from guimauve.models.area import Area


def monitor(left, top, width, height) -> dict:
    return {"left": left, "top": top, "width": width, "height": height}


class FakeMss:
    """Stands in for mss: two screens, the second one left of the primary."""

    monitors = [monitor(-1280, 0, 3200, 1080), monitor(0, 0, 1920, 1080), monitor(-1280, 0, 1280, 1024)]
    grabbed: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def grab(self, region):
        FakeMss.grabbed.append(region)
        return np.zeros((region["height"], region["width"], 4), dtype=np.uint8)


# --- numbering, through screens() ---


@pytest.fixture
def driver(monkeypatch):
    # keyboard and mouse controllers are not used here and would need a display
    monkeypatch.setattr(local_module.pynput.keyboard, "Controller", object)
    monkeypatch.setattr(local_module.pynput.mouse, "Controller", object)
    monkeypatch.setattr(local_module, "mss", FakeMss)
    monkeypatch.setattr(FakeMss, "grabbed", [])
    return LocalDriver()


def screens_for(driver, monkeypatch, *monitors):
    monkeypatch.setattr(FakeMss, "monitors", list(monitors))
    return driver.screens()


def test_single_screen(driver, monkeypatch):
    assert screens_for(driver, monkeypatch, monitor(0, 0, 1920, 1080), monitor(0, 0, 1920, 1080)) == [
        Screen(0, 0, 1920, 1080),
        Screen(0, 0, 1920, 1080),
    ]


def test_primary_is_the_screen_at_the_origin_whatever_the_mss_order(driver, monkeypatch):
    screens = screens_for(
        driver, monkeypatch, monitor(0, 0, 3840, 1080), monitor(1920, 0, 1920, 1080), monitor(0, 0, 1920, 1080)
    )
    assert screens[1:] == [Screen(0, 0, 1920, 1080), Screen(1920, 0, 1920, 1080)]


def test_screens_left_of_and_above_the_primary_have_negative_offsets(driver, monkeypatch):
    screens = screens_for(
        driver,
        monkeypatch,
        monitor(-1920, -1080, 3840, 2160),
        monitor(0, 0, 1920, 1080),
        monitor(-1920, 0, 1920, 1080),
        monitor(0, -1080, 1920, 1080),
    )
    assert screens[1:] == [Screen(0, 0, 1920, 1080), Screen(-1920, 0, 1920, 1080), Screen(0, -1080, 1920, 1080)]


def test_other_screens_are_sorted_left_to_right_then_top_to_bottom(driver, monkeypatch):
    screens = screens_for(
        driver,
        monkeypatch,
        monitor(0, 0, 5760, 2160),
        monitor(3840, 0, 1920, 1080),
        monitor(1920, 1080, 1920, 1080),
        monitor(0, 0, 1920, 1080),
        monitor(1920, 0, 1920, 1080),
    )
    assert [(s.left, s.top) for s in screens[2:]] == [(1920, 0), (1920, 1080), (3840, 0)]


def test_first_listed_screen_is_primary_when_none_is_at_the_origin(driver, monkeypatch):
    screens = screens_for(
        driver, monkeypatch, monitor(0, 0, 3840, 1200), monitor(1920, 0, 1920, 1080), monitor(0, 120, 1920, 1080)
    )
    assert screens[1:] == [Screen(1920, 0, 1920, 1080), Screen(0, 120, 1920, 1080)]


# --- capture ---


@pytest.mark.parametrize(
    ("screen", "region"),
    [
        (1, monitor(0, 0, 1920, 1080)),
        (2, monitor(-1280, 0, 1280, 1024)),
        (0, monitor(-1280, 0, 3200, 1080)),
    ],
)
def test_capture_grabs_the_requested_screen(driver, screen, region):
    image = driver.capture(screen)
    assert FakeMss.grabbed == [region]
    assert image.shape == (region["height"], region["width"], 3)


def test_capture_area_is_relative_to_the_screen(driver):
    image = driver.capture(2, Area(left=10, top=20, right=110, bottom=70))
    assert FakeMss.grabbed == [monitor(-1270, 20, 100, 50)]
    assert image.shape == (50, 100, 3)


def test_capture_rejects_an_area_beyond_the_screen(driver):
    with pytest.raises(ValueError, match="exceeds the size of screen 2"):
        driver.capture(2, Area(left=0, top=0, right=1920, bottom=1080))


def test_capture_rejects_a_missing_screen(driver):
    with pytest.raises(ValueError, match="Screen 3 does not exist: 2 screens available"):
        driver.capture(3)


def test_screens_lists_the_numbered_screens(driver):
    assert driver.screens() == [
        Screen(-1280, 0, 3200, 1080),
        Screen(0, 0, 1920, 1080),
        Screen(-1280, 0, 1280, 1024),
    ]
