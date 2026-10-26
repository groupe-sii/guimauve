from contextlib import contextmanager

import numpy as np
import pytest

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.services import CaptureService
from guimauve.gui.element_editor_next.services import capture as capture_module
from guimauve.gui.element_editor_next.system import ScreenMap

SCREENS = [Screen(0, 0, 300, 100), Screen(0, 0, 100, 100), Screen(100, 0, 200, 100)]


class Driver:
    """Captures a screen as an image filled with its number; records whether the windows were kept out."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[tuple[int, bool]] = []
        self.excluding = False

    def capture(self, number: int) -> np.ndarray:
        self.calls.append((number, self.excluding))
        if self.fail:
            raise RuntimeError("No screen")
        return np.full((10, 10, 3), number, np.uint8)


@pytest.fixture
def driver(monkeypatch):
    fake = Driver()

    @contextmanager
    def out_of_capture(windows):
        fake.excluding = True
        try:
            yield
        finally:
            fake.excluding = False

    monkeypatch.setattr(capture_module, "out_of_capture", out_of_capture)
    return fake


@pytest.fixture
def service(driver, qapp):
    return CaptureService(driver.capture, ScreenMap(SCREENS), tick_ms=10)


def numbers(captures) -> dict[int, int]:
    return {number: int(image[0, 0, 0]) for number, image in captures.items()}


def test_initial_captures_of_every_screen_before_the_windows_show(service, driver):
    assert service.take_initial()

    assert numbers(service.initial()) == {1: 1, 2: 2}
    assert driver.calls == [(1, False), (2, False)]


def test_remote_screen_is_captured_alone(driver, qapp):
    service = CaptureService(driver.capture, ScreenMap([]))

    service.take_initial()

    assert numbers(service.initial()) == {1: 1}


def test_capture_now_keeps_the_windows_out(service, driver, qtbot):
    with qtbot.waitSignal(service.captured):
        service.capture_now()

    assert numbers(service.last()) == {1: 1, 2: 2}
    assert driver.calls == [(1, True), (2, True)]


def test_failure_of_the_driver(service, driver, qtbot):
    driver.fail = True

    assert not service.take_initial()
    assert service.initial() == {}
    with qtbot.waitSignal(service.failed):
        service.capture_now()
    assert service.error == "No screen"
    assert service.last() == {}


def test_countdown(service, driver, qtbot):
    counted = []
    service.countdown_changed.connect(lambda: counted.append(service.remaining))

    with qtbot.waitSignal(service.captured, timeout=1000):
        service.capture_later(3)

    assert counted == [3, 2, 1, None]
    assert driver.calls == [(1, True), (2, True)]  # the windows stay in until the capture


def test_cancel_the_countdown(service, driver, qtbot):
    service.capture_later(3)

    with qtbot.waitSignal(service.countdown_changed):
        service.cancel()

    assert service.remaining is None
    qtbot.wait(60)
    assert driver.calls == []


def test_a_countdown_restarts(service, driver, qtbot):
    service.capture_later(5)

    service.capture_later(2)

    assert service.remaining == 2
    with qtbot.waitSignal(service.captured, timeout=1000):
        pass
    assert len(driver.calls) == 2


def test_no_delay_captures_now(service, driver, qtbot):
    with qtbot.waitSignal(service.captured):
        service.capture_later(0)


def test_capture_runs_in_a_thread(service, driver, qtbot):
    with qtbot.waitSignal(service.capturing_changed):
        service.capture_now()
    assert service.is_capturing()

    with qtbot.waitSignal(service.captured):
        pass
    assert not service.is_capturing()


def test_one_capture_at_a_time(service, driver, qtbot):
    service.capture_now()
    service.capture_now()

    qtbot.waitSignal(service.captured).wait()
    qtbot.wait(30)
    assert len(driver.calls) == 2  # one capture of the two screens


def test_shutdown_waits_for_the_capture(service, driver, qtbot):
    service.capture_now()

    with qtbot.assertNotEmitted(service.captured, wait=30):
        service.shutdown()

    assert not service.is_capturing()
