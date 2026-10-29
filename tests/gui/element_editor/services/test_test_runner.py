import time

import numpy as np
import pytest

from guimauve.detection.detector import Match, Point
from guimauve.detection.locate import LocateReport
from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.services import TestRunner, grabber, used_match
from guimauve.gui.element_editor_next.state import TestScope
from guimauve.models.element import Element

# Screen 2 on the left of the primary screen, a gap of 2 pixels below it.
SCREENS = [Screen(-4, 0, 8, 4), Screen(0, 0, 4, 4), Screen(-4, 0, 4, 2)]


def match(x: int) -> Match:
    return Match(None, Point(x, 0), 0.9)


def capture(value: int, height: int = 4) -> np.ndarray:
    return np.full((height, 4, 3), value, np.uint8)


def test_grab_gives_the_capture_of_a_screen():
    grab = grabber({1: capture(1), 2: capture(2, 2)}, SCREENS)

    assert grab(2)[0, 0, 0] == 2


def test_grab_of_screen_zero_puts_each_capture_at_its_place():
    desktop = grabber({1: capture(1), 2: capture(2, 2)}, SCREENS)(0)

    assert desktop.shape == (4, 8, 3)
    assert (desktop[0, 0, 0], desktop[3, 0, 0], desktop[3, 4, 0]) == (2, 0, 1)  # screen 2, the gap, screen 1


def test_grab_without_screens_gives_the_only_capture():
    assert grabber({1: capture(7)}, [])(3)[0, 0, 0] == 7


def test_grab_of_a_screen_not_captured_fails():
    with pytest.raises(ValueError, match="Screen 2 was not captured"):
        grabber({1: capture(1)}, SCREENS)(2)


@pytest.mark.parametrize(
    ("count", "index", "expected"),
    [
        (2, 1, (1, None)),
        (0, 0, (None, None)),
        (1, 1, (None, "Index 1 out of 1 match")),
        (2, 3, (None, "Index 3 out of 2 matches")),
    ],
)
def test_used_match(count, index, expected):
    assert used_match(LocateReport([match(x) for x in range(count)]), index) == expected


def test_a_fixed_position_is_always_used():
    assert used_match(LocateReport([match(0)], fixed_position=True), 2) == (0, None)


def run(qtbot, runner: TestRunner, element: Element | None = None, **kwargs) -> None:
    with qtbot.waitSignal(runner.finished, timeout=5000):
        runner.run(element or Element(name="button", match_index=1), {1: capture(1)}, SCREENS, **kwargs)


def start(runner: TestRunner, name: str) -> None:
    runner.run(Element(name=name), {1: capture(1)}, SCREENS, TestScope.VARIANT, None, True)


@pytest.fixture
def calls():
    return []


def test_run_gives_the_result(qtbot, calls):
    def locate(element, grab, screens, mouse, stopped):
        calls.append((element.name, grab(1)[0, 0, 0], screens, mouse, stopped()))
        return LocateReport([match(1), match(2)])

    runner = TestRunner((5, 6), locate=locate)
    run(qtbot, runner, scope=TestScope.ELEMENT, variant=None, include_code=False)

    result = runner.result
    assert calls == [("button", 1, SCREENS, (5, 6), False)]
    assert (result.scope, result.include_code, result.used, result.error) == (TestScope.ELEMENT, False, 1, None)
    assert result.used_match == match(2)
    assert result.captures[1][0, 0, 0] == 1 and result.duration >= 0
    assert not runner.is_running()


def test_a_failure_of_the_search_is_the_error_of_the_result(qtbot):
    def locate(*_):
        raise ValueError("Area exceeds screen 1")

    runner = TestRunner((0, 0), locate=locate)
    run(qtbot, runner, scope=TestScope.VARIANT, variant=3, include_code=True)

    assert (runner.result.report, runner.result.error, runner.result.variant) == (None, "Area exceeds screen 1", 3)


class Slow:
    """Locate whose search named "slow" runs until it is stopped; records the searches and how they overlap."""

    def __init__(self):
        self.started: list[str] = []
        self.stopped: list[str] = []
        self.running = 0
        self.most = 0

    def __call__(self, element, grab, screens, mouse, stopped):
        self.started.append(element.name)
        self.running += 1
        self.most = max(self.most, self.running)
        try:
            if element.name == "slow":
                deadline = time.monotonic() + 5
                while not stopped() and time.monotonic() < deadline:
                    time.sleep(0.005)
                self.stopped.append(element.name)
                raise RuntimeError("stopped")
            return LocateReport([match(len(self.started))])
        finally:
            self.running -= 1


def test_a_new_run_stops_the_one_in_progress_then_starts(qtbot):
    slow = Slow()
    runner = TestRunner((0, 0), locate=slow)
    start(runner, "slow")
    qtbot.waitUntil(lambda: slow.started == ["slow"])

    run(qtbot, runner, Element(name="fast"), scope=TestScope.VARIANT, variant=None, include_code=True)

    assert slow.stopped == ["slow"] and slow.started == ["slow", "fast"]
    assert slow.most == 1  # never two searches at once
    assert runner.result.error is None and runner.result.used_match == match(2)


def test_only_the_last_run_asked_waits(qtbot):
    slow = Slow()
    runner = TestRunner((0, 0), locate=slow)
    start(runner, "slow")
    qtbot.waitUntil(lambda: slow.started == ["slow"])
    start(runner, "forgotten")

    run(qtbot, runner, Element(name="last"), scope=TestScope.VARIANT, variant=None, include_code=True)

    assert slow.started == ["slow", "last"]


def test_cancel_stops_the_search_without_result(qtbot):
    slow = Slow()
    runner = TestRunner((0, 0), locate=slow)
    start(runner, "slow")
    qtbot.waitUntil(lambda: slow.started == ["slow"])

    runner.cancel()
    assert not runner.is_running()
    qtbot.waitUntil(lambda: slow.stopped == ["slow"])
    qtbot.wait(20)  # lets the end of the search arrive

    assert runner.result is None


def test_shutdown_stops_and_waits_for_the_search(qtbot):
    slow = Slow()
    runner = TestRunner((0, 0), locate=slow)
    start(runner, "slow")
    qtbot.waitUntil(lambda: slow.started == ["slow"])

    runner.shutdown()

    assert slow.stopped == ["slow"] and not runner.is_running()
