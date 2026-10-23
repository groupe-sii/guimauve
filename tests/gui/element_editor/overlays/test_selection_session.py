import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.overlays import Selection, SelectionMode, SelectionSession
from guimauve.gui.element_editor_next.system import ScreenMap

LEFT, NONE = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton


def capture(width=200, height=100):
    return np.zeros((height, width, 3), np.uint8)


def mouse(widget, kind, x, y, button=NONE, buttons=NONE) -> None:
    point = QPointF(x, y)
    QApplication.sendEvent(widget, QMouseEvent(kind, point, point, button, buttons, Qt.KeyboardModifier.NoModifier))


def drag(widget, start, end) -> None:
    mouse(widget, QEvent.Type.MouseButtonPress, *start, LEFT, LEFT)
    mouse(widget, QEvent.Type.MouseMove, *end, NONE, LEFT)
    mouse(widget, QEvent.Type.MouseButtonRelease, *end, LEFT, NONE)


@pytest.fixture
def session(qapp):
    made = []

    def make(captures=None, mode=SelectionMode.AREA) -> SelectionSession:
        captures = captures or {1: capture(), 2: capture(400, 100)}
        made.append(selection := SelectionSession(captures, ScreenMap([]), mode))  # both fitted on the primary screen
        return selection

    yield make
    for selection in made:
        selection.cancel()


def test_session_numbers_the_screens(session):
    selection = session()

    assert set(selection.overlays) == {1, 2}
    assert all(overlay.shows_number() for overlay in selection.overlays.values())


def test_a_drag_hides_the_numbers(session):
    selection = session()

    selection.overlays[1].drag_started.emit()

    assert not any(overlay.shows_number() for overlay in selection.overlays.values())


def test_session_ends_with_the_area_selected(session, qtbot):
    selection = session()
    selection.start()
    overlay = selection.overlays[1]
    shown = overlay.shown_rect()
    start, end = shown.topLeft() + QPointF(1, 1), shown.topLeft() + QPointF(40, 30)

    with qtbot.waitSignal(selection.finished):
        drag(overlay, (start.x(), start.y()), (end.x(), end.y()))

    assert selection.result is not None
    assert selection.result.screen == 1
    assert selection.result.area is not None and selection.result.area.width > 1
    assert selection.overlays == {}


def test_session_ends_with_the_point_selected(session, qtbot):
    selection = session({1: capture()}, SelectionMode.POINT)
    overlay = selection.overlays[1]
    corner = overlay.shown_rect().topLeft()

    with qtbot.waitSignal(selection.finished):
        drag(overlay, (corner.x() + 0.5, corner.y() + 0.5), (corner.x() + 0.5, corner.y() + 0.5))

    assert selection.result == Selection(1, point=(0, 0))


def test_session_cancelled(session, qtbot):
    selection = session()

    with qtbot.waitSignal(selection.finished):
        selection.overlays[1].cancelled.emit()

    assert selection.result is None


def test_remote_screen_shows_its_scale(session):
    primary = QApplication.primaryScreen().geometry()

    selection = session({1: capture(primary.width() * 2, primary.height() * 2)}, SelectionMode.POINT)

    overlay = selection.overlays[1]
    assert overlay.note == "Remote screen at 50 %."
    assert not overlay.shows_number()
