import cv2 as cv
import numpy
import pytest

from guimauve.drivers.driver import Driver
from guimauve.enums import Button, Key
from guimauve.models.area import Area


class FakeDriver(Driver):
    """Driver that records every call instead of executing anything.

    `screen` is the image returned by `capture` (RGB), `position` the mouse position.
    """

    def __init__(self, width: int = 1920, height: int = 1080):
        self.calls: list[tuple] = []
        self.screen = numpy.zeros((height, width, 3), dtype=numpy.uint8)
        self.position = (0, 0)

    def capture(self, area: Area | None = None) -> numpy.ndarray:
        self.calls.append(("capture", area))
        if area is None:
            return self.screen.copy()
        return self.screen[area.top : area.bottom, area.left : area.right].copy()

    def key_down(self, key: Key):
        self.calls.append(("key_down", key))

    def key_up(self, key: Key):
        self.calls.append(("key_up", key))

    def mouse_down(self, button: Button):
        self.calls.append(("mouse_down", button))

    def mouse_up(self, button: Button):
        self.calls.append(("mouse_up", button))

    def mouse_move(self, x: int, y: int):
        self.calls.append(("mouse_move", x, y))
        self.position = (x, y)

    def mouse_scroll(self, v: int, h: int):
        self.calls.append(("mouse_scroll", v, h))

    def mouse_position(self) -> tuple[int, int]:
        self.calls.append(("mouse_position",))
        return self.position

    def paste(self, text: str):
        self.calls.append(("paste", text))

    def type(self, text: str):
        self.calls.append(("type", text))

    def connect(self):
        self.calls.append(("connect",))

    def close(self):
        self.calls.append(("close",))


@pytest.fixture
def fake_driver():
    return FakeDriver()


class FakeListener:
    """Stand-in for pynput.keyboard.Listener and pynput.mouse.Listener."""

    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False

    @property
    def running(self) -> bool:
        return self.started and not self.stopped

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.fixture
def fake_listener_cls():
    return FakeListener


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
    """Replaces every detector used for location with a FakeDetector, keyed by detection name."""
    import guimauve.detection.locate as locate_module  # imported here: it loads the OCR engine

    fakes = {name: FakeDetector() for name in locate_module.DETECTORS}
    for name, fake in fakes.items():
        monkeypatch.setitem(locate_module.DETECTORS, name, lambda fake=fake: fake)
    return fakes


class FakeOcr:
    """Stands in for the Ocr class used to locate and read text."""

    calls: list[tuple] = []
    matches: list = []

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
    """Replaces the Ocr class used for location with FakeOcr."""
    import guimauve.detection.locate as locate_module  # imported here: it loads the OCR engine

    monkeypatch.setattr(locate_module, "Ocr", FakeOcr)
    monkeypatch.setattr(FakeOcr, "calls", [])
    monkeypatch.setattr(FakeOcr, "matches", [])
    return FakeOcr


@pytest.fixture
def needle():
    return numpy.zeros((40, 60, 3), dtype=numpy.uint8)


@pytest.fixture
def needle_path(tmp_path, needle):
    """Image file for ImageVariant, whose path must exist; its content is irrelevant with fake detectors."""
    path = tmp_path / "needle.png"
    cv.imwrite(str(path), needle)
    return path
