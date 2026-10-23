from contextlib import contextmanager

import numpy as np
import pytest
from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.canvas.region import Region
from guimauve.gui.element_editor_next.overlays import Selection
from guimauve.gui.element_editor_next.panels import image_files
from guimauve.gui.element_editor_next.panels.capture_flow import DEFAULT_DELAY, NO_INITIAL, CaptureFlow
from guimauve.gui.element_editor_next.services import CaptureService, CaptureSource
from guimauve.gui.element_editor_next.services import capture as capture_module
from guimauve.gui.element_editor_next.system import ScreenMap


def screen(value: int) -> np.ndarray:
    """Capture whose pixels tell where they come from: the screen, then the column."""
    image = np.zeros((50, 80, 3), np.uint8)
    image[..., 0] = value
    image[..., 1] = np.arange(80)[None, :]
    return image


class Session(QObject):
    """Selection answered by the test: it records the captures and ends with the result given."""

    finished = Signal()
    opened: list["Session"] = []

    def __init__(self, captures):
        super().__init__()
        self.captures = captures
        self.result: Selection | None = None
        Session.opened.append(self)

    def start(self):
        pass

    def cancel(self):
        self.end(None)

    def end(self, result: Selection | None) -> None:
        self.result = result
        self.finished.emit()


@pytest.fixture(autouse=True)
def no_exclusion(monkeypatch):
    @contextmanager
    def out_of_capture(windows):
        yield

    monkeypatch.setattr(capture_module, "out_of_capture", out_of_capture)
    Session.opened = []


@pytest.fixture
def make_flow(store, qtbot, tmp_path):
    def make(fail_initial=False, count=None):
        count = count if count is not None else iter(range(1, 100))

        def provider(number):
            if fail_initial:
                raise RuntimeError("No display")
            return screen(10 * next(count) + number)

        window = QWidget()
        qtbot.addWidget(window)
        service = CaptureService(provider, ScreenMap([]), tick_ms=10)
        service.take_initial()
        settings = QSettings(str(tmp_path / "editor.ini"), QSettings.Format.IniFormat)
        return CaptureFlow(store, service, settings, window, Session)

    return make


def light(store) -> int:
    return store.variant_keys()[0]


AREA = Selection(1, area=Region(5, 10, 25, 30))


def test_initial_screen_replaces_the_image(store, make_flow):
    flow = make_flow()
    targets = list(store.document.variants[0].targets)

    flow.capture(CaptureSource.INITIAL, light(store))
    Session.opened[-1].end(AREA)

    image = store.document.variants[0].image
    assert image.shape[:2] == (20, 20)
    assert (image[0, 0, 0], image[0, 0, 1]) == (11, 5)  # the initial capture, from its column 5
    assert store.document.variants[0].targets == targets
    assert not flow.is_busy()


def test_capture_for_a_new_variant(store, make_flow):
    flow = make_flow()
    count = len(store.document.variants)

    flow.capture(CaptureSource.INITIAL)
    Session.opened[-1].end(AREA)

    assert len(store.document.variants) == count + 1
    assert store.selected_variant == store.variant_keys()[-1]
    assert store.document.variants[-1].image.shape[:2] == (20, 20)


def test_cancelled_selection_changes_nothing(store, make_flow):
    flow = make_flow()
    image = store.document.variants[0].image

    flow.capture(CaptureSource.INITIAL, light(store))
    Session.opened[-1].end(None)

    assert store.document.variants[0].image is image
    assert not store.can_undo


def test_instant_capture_takes_new_captures(store, make_flow, qtbot):
    flow = make_flow()

    flow.capture(CaptureSource.INSTANT, light(store))

    assert int(Session.opened[-1].captures[1][0, 0, 0]) == 21  # second capture, after the initial one


def test_delayed_capture_counts_down(store, make_flow, qtbot):
    flow = make_flow()
    flow.set_delay(2)
    seen = []
    flow.changed.connect(lambda: seen.append(flow.remaining))

    flow.capture(CaptureSource.DELAYED, light(store))
    assert flow.remaining == 2
    assert flow.is_busy()
    qtbot.waitUntil(lambda: bool(Session.opened), timeout=1000)

    assert 1 in seen
    assert flow.remaining is None


def test_countdown_cancelled(store, make_flow, qtbot):
    flow = make_flow()

    flow.capture(CaptureSource.DELAYED, light(store))
    flow.cancel()

    qtbot.wait(60)
    assert Session.opened == []
    assert not flow.is_busy()


def test_one_capture_at_a_time(store, make_flow):
    flow = make_flow()

    flow.capture(CaptureSource.INITIAL, light(store))
    flow.capture(CaptureSource.INITIAL, light(store))

    assert len(Session.opened) == 1


def test_delay_is_kept_within_bounds(make_flow):
    flow = make_flow()
    assert flow.delay == DEFAULT_DELAY

    flow.set_delay(500)

    assert flow.delay == 60


def test_failed_capture_shows_the_error(store, make_flow):
    def failing():
        yield 1
        raise RuntimeError("Driver lost")

    flow = make_flow(count=failing())

    flow.capture(CaptureSource.INSTANT, light(store))

    assert flow.error == "Capture failed: Driver lost"
    assert not flow.is_busy()
    flow.clear_error()
    assert flow.error is None


def test_no_initial_captures(make_flow):
    flow = make_flow(fail_initial=True)

    assert flow.initial_error == "No display"


def test_no_initial_captures_without_message(store, qtbot, tmp_path):
    window = QWidget()
    qtbot.addWidget(window)
    service = CaptureService(lambda number: screen(1), ScreenMap([]))  # take_initial never called
    flow = CaptureFlow(store, service, QSettings(str(tmp_path / "e.ini"), QSettings.Format.IniFormat), window, Session)

    assert flow.initial_error == NO_INITIAL


def test_import_a_file(store, make_flow, monkeypatch, tmp_path):
    import cv2 as cv  # noqa: PLC0415

    path = tmp_path / "button.png"
    cv.imwrite(str(path), np.zeros((12, 30, 3), np.uint8))
    monkeypatch.setattr(image_files, "ask_image_file", lambda parent: path)
    flow = make_flow()

    flow.capture(CaptureSource.FILE, light(store))

    assert store.document.variants[0].image.shape[:2] == (12, 30)


def test_unreadable_file(store, make_flow, monkeypatch, tmp_path):
    warnings = []
    monkeypatch.setattr(image_files, "ask_image_file", lambda parent: tmp_path / "notes.png")
    monkeypatch.setattr(image_files, "warn", lambda parent, text: warnings.append(text))
    flow = make_flow()

    flow.capture(CaptureSource.FILE, light(store))

    assert warnings == [image_files.UNREADABLE]
    assert not store.can_undo


def test_variant_deleted_meanwhile(store, make_flow):
    flow = make_flow()
    key = light(store)

    flow.capture(CaptureSource.INITIAL, key)
    store.remove_variant(key)
    count = len(store.document.variants)
    Session.opened[-1].end(AREA)

    assert len(store.document.variants) == count
