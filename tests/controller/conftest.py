import cv2 as cv
import numpy as np
import pytest

import guimauve.controller as controller_module
from guimauve.controller import Controller

# Calls issued by the controller itself (bookkeeping, logging) rather than by the action under test.
_NOISE = {"mouse_position", "capture"}


@pytest.fixture
def sleeps(monkeypatch):
    """Records every delay passed to the controller's sleep instead of waiting."""
    recorded: list[float] = []
    monkeypatch.setattr(controller_module, "sleep_", recorded.append)
    return recorded


@pytest.fixture
def make_controller(monkeypatch, fake_driver, fake_listener_cls, sleeps):
    """Builds a Controller wired to the fake driver, without any real pynput listener."""
    monkeypatch.setattr("guimauve.pause_manager.Listener", fake_listener_cls)
    monkeypatch.setitem(controller_module.DRIVERS, "local", lambda **_: fake_driver)

    def factory(*, parameters=None) -> Controller:
        return Controller(parameters=parameters)

    return factory


@pytest.fixture
def controller(make_controller):
    return make_controller()


@pytest.fixture
def inputs(fake_driver):
    """Returns the driver calls that reach the system, without the controller's bookkeeping."""

    def filtered() -> list[tuple]:
        return [call for call in fake_driver.calls if call[0] not in _NOISE]

    return filtered


class FakeDetector:
    """Stands in for a Detector: records each call and returns the configured matches."""

    def __init__(self):
        self.calls: list[dict] = []
        self.matches: list = []

    def locate(self, needle, haystack, **kwargs):
        self.calls.append({"needle": needle, "haystack": haystack, **kwargs})
        return list(self.matches)


@pytest.fixture
def detectors(monkeypatch):
    """Replaces every detector the controller can pick with a FakeDetector, keyed by detection name."""
    fakes = {name: FakeDetector() for name in controller_module.DETECTORS}
    for name, fake in fakes.items():
        monkeypatch.setitem(controller_module.DETECTORS, name, lambda fake=fake: fake)
    return fakes


@pytest.fixture
def needle():
    return np.zeros((40, 60, 3), dtype=np.uint8)


@pytest.fixture
def needle_path(tmp_path, needle):
    """Image file for ImageVariant, whose path must exist; its content is irrelevant with fake detectors."""
    path = tmp_path / "needle.png"
    cv.imwrite(str(path), needle)
    return path
