import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QGuiApplication

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.system import ScreenGeometry, ScreenMap, match_screens, to_logical, to_physical

# A 4K screen at 150 % on the left of a primary full HD screen at 100 %, as mss and Qt list them under Windows
LEFT_4K = Screen(-3840, 0, 3840, 2160)
PRIMARY = Screen(0, 0, 1920, 1080)
DRIVER = [Screen(-3840, 0, 5760, 2160), PRIMARY, LEFT_4K]
QT_PRIMARY = ScreenGeometry(0, 0, 1920, 1080, 1.0)
QT_4K = ScreenGeometry(-3840, 0, 2560, 1440, 1.5)  # native origin, logical size


def test_match_by_origin_and_physical_size():
    assert match_screens(DRIVER, [QT_4K, QT_PRIMARY]) == {1: 1, 2: 0}


def test_match_by_origin_when_the_size_differs():
    rounded = ScreenGeometry(-3840, 0, 2561, 1441, 1.5)

    assert match_screens(DRIVER, [rounded, QT_PRIMARY]) == {1: 1, 2: 0}


def test_match_by_position_order_when_qt_scales_the_origins():
    scaled = ScreenGeometry(-2560, 0, 2560, 1440, 1.5)  # as macOS would

    assert match_screens(DRIVER, [QT_PRIMARY, scaled]) == {1: 0, 2: 1}


def test_screen_without_qt_screen_is_left_out():
    assert match_screens(DRIVER, [QT_PRIMARY]) == {1: 0}


def test_no_screens_from_the_driver():
    assert match_screens([], [QT_PRIMARY]) == {}


@pytest.mark.parametrize(
    ("physical", "logical"),
    [
        (QPointF(0, 0), QPointF(-3840, 0)),
        (QPointF(300, 150), QPointF(-3640, 100)),
        (QPointF(3840, 2160), QPointF(-1280, 1440)),
    ],
)
def test_conversions_on_a_scaled_screen(physical, logical):
    assert to_logical(QT_4K, physical) == logical
    assert to_physical(QT_4K, logical) == physical


def test_map_of_the_application_screens(qapp):
    qt = QGuiApplication.primaryScreen()
    rect = qt.geometry()
    ratio = qt.devicePixelRatio()
    size = (round(rect.width() * ratio), round(rect.height() * ratio))
    primary = Screen(rect.x(), rect.y(), *size)

    screens = ScreenMap([primary, primary])

    assert not screens.is_remote
    assert screens.numbers() == [1]
    assert screens.qt_screen(1) is qt
    assert screens.driver_screen(1) == primary
    assert screens.to_physical(1, screens.to_logical(1, QPointF(10, 20))) == QPointF(10, 20)


def test_remote_screen(qapp):
    screens = ScreenMap([])

    assert screens.is_remote
    assert screens.numbers() == [1]
    assert screens.qt_screen(1) is None
    assert screens.driver_screen(1) is None
    assert screens.to_logical(1, QPointF(1, 1)) is None


def test_screens_of_the_application_are_read_at_each_use(qapp, monkeypatch):
    qt = QGuiApplication.primaryScreen()
    rect = qt.geometry()
    primary = Screen(
        rect.x(), rect.y(), round(rect.width() * qt.devicePixelRatio()), round(rect.height() * qt.devicePixelRatio())
    )
    screens = ScreenMap([primary, primary])

    monkeypatch.setattr(QGuiApplication, "screens", staticmethod(lambda: []))  # replaced, e.g. a display change

    assert screens.qt_screen(1) is None


def test_desktop_is_the_screen_0_of_the_driver(qapp):
    desktop = Screen(-100, 0, 300, 100)

    assert ScreenMap([desktop, Screen(0, 0, 200, 100)], qt_screens=[]).desktop() == desktop
    assert ScreenMap([]).desktop() is None
