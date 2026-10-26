import numpy as np
import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.canvas.region import Region
from guimauve.gui.element_editor_next.overlays import Selection, SelectionMode
from guimauve.gui.element_editor_next.panels import ScreenPicker
from guimauve.gui.element_editor_next.panels.screen_picker import offset, screens_offered
from guimauve.gui.element_editor_next.services import CaptureService
from guimauve.gui.element_editor_next.system import ScreenMap
from guimauve.models.area import Area

# A screen on the left of the primary one, as mss lists them
DESKTOP = Screen(-1280, 0, 3200, 1080)
PRIMARY = Screen(0, 0, 1920, 1080)
LEFT = Screen(-1280, 100, 1280, 800)
SCREENS = ScreenMap([DESKTOP, PRIMARY, LEFT], qt_screens=[])

POINT, AREA = SelectionMode.POINT, SelectionMode.AREA


@pytest.mark.parametrize(
    ("screen", "mode", "expected"),
    [
        (None, POINT, [1]),
        (2, AREA, [2]),
        (0, POINT, [1, 2]),
        ([2, 1], POINT, [2]),  # a point applies to the first screen of the list
        ([2, 1], AREA, [2, 1]),  # an area to each
        (5, POINT, [1]),  # not captured: the first screen
    ],
)
def test_screens_offered(screen, mode, expected):
    assert screens_offered(screen, mode, [1, 2]) == expected


def test_no_offset_on_a_screen():
    assert offset(Selection(2, point=(10, 20)), 2, SCREENS) == (0, 0)


def test_point_from_the_primary_screen_with_screen_0():
    assert offset(Selection(2, point=(10, 20)), 0, SCREENS) == (-1280, 100)


def test_area_from_the_whole_desktop_with_screen_0():
    assert offset(Selection(1, area=Region(0, 0, 5, 5)), 0, SCREENS) == (1280, 0)


def test_no_offset_on_a_remote_screen():
    assert offset(Selection(1, point=(10, 20)), 0, ScreenMap([])) == (0, 0)


class Session(QObject):
    finished = Signal()

    def __init__(self, captures, mode):
        super().__init__()
        self.captures, self.mode, self.result = captures, mode, None
        Session.last = self

    def start(self):
        pass

    def end(self, result):
        self.result = result
        self.finished.emit()


@pytest.fixture
def picker(qtbot):
    def make(screens=SCREENS, fail=False):
        def provider(number):
            if fail:
                raise RuntimeError("No display")
            return np.zeros((10, 10, 3), np.uint8)

        window = QWidget()
        qtbot.addWidget(window)
        service = CaptureService(provider, screens)
        service.take_initial()
        return ScreenPicker(service, window, Session)

    return make


def test_pick_a_point(picker):
    points = []

    picker().pick_point(0, lambda x, y: points.append((x, y)))
    assert set(Session.last.captures) == {1, 2}
    assert Session.last.mode is POINT
    Session.last.end(Selection(2, point=(10, 20)))

    assert points == [(-1270, 120)]


def test_draw_an_area(picker):
    areas = []

    picker().pick_area(2, areas.append)
    assert set(Session.last.captures) == {2}
    Session.last.end(Selection(2, area=Region(1, 2, 30, 40)))

    assert areas == [Area(left=1, top=2, right=30, bottom=40)]


def test_cancelled_gives_nothing(picker):
    points = []

    picker().pick_point(None, lambda x, y: points.append((x, y)))
    Session.last.end(None)

    assert points == []


def test_unavailable_without_initial_captures(picker):
    assert picker().unavailable is None
    assert picker(fail=True).unavailable == "No display"
