from typing import Optional

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

    def capture(self, area: Optional[Area] = None) -> numpy.ndarray:
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
