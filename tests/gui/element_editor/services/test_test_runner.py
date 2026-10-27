import threading

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


@pytest.fixture
def calls():
    return []


def test_run_gives_the_result(qtbot, calls):
    def locate(element, grab, screens, mouse):
        calls.append((element.name, grab(1)[0, 0, 0], screens, mouse))
        return LocateReport([match(1), match(2)])

    runner = TestRunner((5, 6), locate=locate)
    run(qtbot, runner, scope=TestScope.ELEMENT, variant=None, include_code=False)

    result = runner.result
    assert calls == [("button", 1, SCREENS, (5, 6))]
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


def test_a_new_run_drops_the_one_in_progress(qtbot):
    release = threading.Event()
    reports = iter([LocateReport([match(1)]), LocateReport([match(2)])])

    def locate(element, *_):
        if element.name == "slow":
            release.wait(5)
        return next(reports)

    runner = TestRunner((0, 0), locate=locate)
    finished: list[int] = []
    runner.finished.connect(lambda: finished.append(runner.result.used_match.target.x))
    runner.run(Element(name="slow"), {1: capture(1)}, SCREENS, TestScope.VARIANT, None, True)
    run(qtbot, runner, Element(name="fast"), scope=TestScope.VARIANT, variant=None, include_code=True)
    release.set()
    runner.shutdown()
    qtbot.wait(10)  # lets the end of the dropped search arrive

    assert finished == [1]


def test_cancel_drops_the_result(qtbot):
    release = threading.Event()

    def locate(*_):
        release.wait(5)
        return LocateReport([match(1)])

    runner = TestRunner((0, 0), locate=locate)
    runner.run(Element(name="button"), {1: capture(1)}, SCREENS, TestScope.VARIANT, None, True)
    assert runner.is_running()

    with qtbot.waitSignal(runner.running_changed):
        runner.cancel()
    release.set()
    runner.shutdown()
    qtbot.wait(10)

    assert runner.result is None and not runner.is_running()
