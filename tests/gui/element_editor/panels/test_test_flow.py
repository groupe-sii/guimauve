from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget

from guimauve.detection.detector import Match, Point
from guimauve.detection.locate import LocateReport
from guimauve.gui.element_editor_next.panels import TestFlow, image_files
from guimauve.gui.element_editor_next.panels import test_flow as flow_module
from guimauve.gui.element_editor_next.services import CaptureService, CaptureSource, TestRunner
from guimauve.gui.element_editor_next.services import capture as capture_module
from guimauve.gui.element_editor_next.state import ELEMENT, Mode, TestScope
from guimauve.gui.element_editor_next.system import ScreenMap


@pytest.fixture(autouse=True)
def no_exclusion(monkeypatch):
    @contextmanager
    def out_of_capture(windows):
        yield

    monkeypatch.setattr(capture_module, "out_of_capture", out_of_capture)


class Locate:
    """Records what each search got: the element, the value of screen 1 and the screens."""

    def __init__(self):
        self.calls: list[tuple] = []

    def __call__(self, element, grab, screens, mouse, stopped):
        self.calls.append((element, int(grab(1)[0, 0, 0]), screens))
        return LocateReport([Match(None, Point(1, 1), 0.9)])


@pytest.fixture
def locate():
    return Locate()


class Driver:
    """Captures screen n of the k-th capture as an image filled with 10 k + n, or fails while failing is set."""

    def __init__(self):
        self.failing = False
        self.count = 0

    def capture(self, number: int) -> np.ndarray:
        if self.failing:
            raise RuntimeError("Driver lost")
        self.count += number == 1
        return np.full((10, 10, 3), 10 * self.count + number, np.uint8)


@pytest.fixture
def driver():
    return Driver()


@pytest.fixture
def make_flow(store, locate, driver, qtbot, tmp_path):
    def make(initial=True):
        window = QWidget()
        qtbot.addWidget(window)
        window.show()
        service = CaptureService(driver.capture, ScreenMap(store.screens), tick_ms=10)
        driver.failing = not initial
        service.take_initial()
        driver.failing = False
        runner = TestRunner((0, 0), window, locate=locate)
        settings = QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat)
        flow = TestFlow(store, service, runner, settings, window)
        return flow, window

    return make


def run_and_wait(qtbot, store, action) -> None:
    with qtbot.waitSignal(store.test_changed, timeout=5000):
        action()


def test_a_request_in_test_mode_runs_on_the_initial_screen(store, make_flow, locate, qtbot):
    flow, _ = make_flow()
    store.set_mode(Mode.TEST)

    run_and_wait(qtbot, store, store.request_test)

    ((element, screen_1, screens),) = locate.calls
    assert [variant.name for variant in element.variants] == ["light"]  # the selected variant
    assert (screen_1, screens) == (11, store.screens)
    assert store.test_result.scope is TestScope.VARIANT and store.test_result.used == 0
    assert flow.source == "Initial screen"


def test_a_request_in_edit_mode_runs_nothing(store, make_flow, locate, qtbot):
    make_flow()

    store.request_test()
    qtbot.wait(20)

    assert locate.calls == [] and store.test_result is None


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        (lambda store: store.set_field(ELEMENT, "timeout", -1), "Fix 1 issue to test"),
        (lambda store: store.select(None), "Select a variant to test it"),
    ],
)
def test_blocked(store, make_flow, setup, reason):
    flow, _ = make_flow()
    setup(store)

    assert flow.blocked() == reason


def test_blocked_without_capture(store, make_flow):
    flow, _ = make_flow(initial=False)

    assert flow.blocked() == "No capture to test on: capture the screens first"


def test_the_element_scope_needs_no_selection(store, make_flow):
    flow, _ = make_flow()
    store.select(None)
    store.set_test_scope(TestScope.ELEMENT)

    assert flow.blocked() is None


def test_instant_capture_becomes_the_capture_without_running(store, make_flow, locate, qtbot):
    flow, _ = make_flow()
    store.set_mode(Mode.TEST)
    run_and_wait(qtbot, store, flow.run)

    with qtbot.waitSignal(store.test_changed, timeout=5000):  # the result is now stale
        flow.capture(CaptureSource.INSTANT)

    assert flow.source.startswith("Captured ") and store.test_stale and len(locate.calls) == 1
    run_and_wait(qtbot, store, flow.run)
    assert locate.calls[-1][1] == 21  # second capture of screen 1, after the initial one
    run_and_wait(qtbot, store, flow.run)
    assert locate.calls[-1][1] == 21  # Run test never captures again


def test_delayed_capture_hides_the_window_until_captured(store, make_flow, qtbot):
    flow, window = make_flow()
    store.set_mode(Mode.TEST)

    flow.capture(CaptureSource.DELAYED)
    assert not window.isVisible() and flow.is_running()

    qtbot.waitUntil(lambda: not flow.is_running(), timeout=5000)
    assert window.isVisible() and flow.source.startswith("Captured ")


def test_failed_capture_keeps_the_capture_and_shows_the_error(store, make_flow, driver, qtbot):
    flow, _ = make_flow()
    driver.failing = True

    with qtbot.waitSignal(flow.changed, check_params_cb=lambda: flow.error is not None, timeout=5000):
        flow.capture(CaptureSource.INSTANT)

    assert flow.error == "Capture failed: Driver lost"
    assert flow.source == "Initial screen" and not flow.is_running()


def test_a_file_is_a_single_screen(store, make_flow, locate, qtbot, monkeypatch):
    flow, _ = make_flow()
    store.set_mode(Mode.TEST)
    monkeypatch.setattr(image_files, "ask_image_file", lambda parent: Path("/tmp/screen.png"))
    monkeypatch.setattr(flow_module, "read_image", lambda path: np.full((10, 10, 3), 7, np.uint8))

    flow.capture(CaptureSource.FILE)
    assert locate.calls == []

    run_and_wait(qtbot, store, flow.run)
    assert locate.calls[-1][1:] == (7, [])
    assert flow.source == "screen.png"


def test_include_code_and_scope_go_to_the_result(store, make_flow, qtbot):
    make_flow()
    store.set_mode(Mode.TEST)
    store.set_include_code(False)
    store.set_test_scope(TestScope.ELEMENT)

    run_and_wait(qtbot, store, store.request_test)

    assert (store.test_result.include_code, store.test_result.variant) == (False, None)


def test_cancel_stops_a_delayed_capture(store, make_flow, qtbot):
    flow, window = make_flow()
    store.set_mode(Mode.TEST)
    flow.capture(CaptureSource.DELAYED)

    flow.cancel()
    qtbot.wait(50)

    assert window.isVisible() and not flow.is_running() and store.test_result is None
