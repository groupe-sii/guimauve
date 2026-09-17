import pytest


class FakeDriver:
    """Driver that records every call instead of executing anything."""

    def __init__(self):
        self.calls = []

    def key_down(self, key):
        self.calls.append(("key_down", key))

    def key_up(self, key):
        self.calls.append(("key_up", key))

    def mouse_move(self, x, y):
        self.calls.append(("mouse_move", x, y))

    def mouse_down(self, button):
        self.calls.append(("mouse_down", button))

    def mouse_up(self, button):
        self.calls.append(("mouse_up", button))

    def mouse_scroll(self, dx, dy):
        self.calls.append(("mouse_scroll", dx, dy))


class FakeListener:
    """Stand-in for pynput.keyboard.Listener and pynput.mouse.Listener."""

    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


@pytest.fixture
def fake_driver():
    return FakeDriver()


@pytest.fixture
def fake_listener_cls():
    return FakeListener
