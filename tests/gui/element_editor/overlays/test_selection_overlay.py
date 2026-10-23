import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.canvas.region import Region
from guimauve.gui.element_editor_next.overlays import SelectionMode, SelectionOverlay
from guimauve.gui.element_editor_next.services.images import to_qimage

LEFT, NONE = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton
CTRL, PLAIN = Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.NoModifier


def capture(width=200, height=100):
    return np.zeros((height, width, 3), np.uint8)


@pytest.fixture
def make(qtbot):
    def overlay(mode=SelectionMode.AREA, shown=None, image=None) -> SelectionOverlay:
        widget = SelectionOverlay(to_qimage(capture() if image is None else image), mode, shown)
        qtbot.addWidget(widget)
        widget.resize(200, 100)
        widget.show()
        return widget

    return overlay


def mouse(widget, kind, x, y, button=NONE, buttons=NONE, modifiers=PLAIN) -> None:
    point = QPointF(x, y)
    QApplication.sendEvent(widget, QMouseEvent(kind, point, point, button, buttons, modifiers))


def drag(widget, start, end, modifiers=PLAIN) -> None:
    mouse(widget, QEvent.Type.MouseButtonPress, *start, LEFT, LEFT)
    mouse(widget, QEvent.Type.MouseMove, *end, NONE, LEFT, modifiers)
    mouse(widget, QEvent.Type.MouseButtonRelease, *end, LEFT, NONE)


def test_drag_selects_an_area(make, qtbot):
    overlay = make()

    with qtbot.waitSignal(overlay.drag_started), qtbot.waitSignal(overlay.selected):
        drag(overlay, (10.5, 20.5), (50.5, 30.5))

    assert overlay.region() == Region(10, 20, 51, 31)


def test_ctrl_moves_the_area(make):
    overlay = make()
    mouse(overlay, QEvent.Type.MouseButtonPress, 10.5, 20.5, LEFT, LEFT)
    mouse(overlay, QEvent.Type.MouseMove, 50.5, 30.5, NONE, LEFT)

    mouse(overlay, QEvent.Type.MouseMove, 60.5, 35.5, NONE, LEFT, CTRL)

    assert overlay.region() == Region(20, 25, 61, 36)
    mouse(overlay, QEvent.Type.MouseMove, 70.5, 35.5, NONE, LEFT)  # Ctrl released: resizes from the moved corner
    assert overlay.region() == Region(20, 25, 71, 36)


def test_click_without_drag_selects_nothing(make, qtbot):
    overlay = make()

    with qtbot.assertNotEmitted(overlay.selected):
        drag(overlay, (10.5, 20.5), (10.5, 20.5))

    assert overlay.region() is None


def test_click_selects_a_point(make, qtbot):
    overlay = make(SelectionMode.POINT)

    with qtbot.waitSignal(overlay.selected):
        drag(overlay, (12.5, 7.5), (12.5, 7.5))

    assert overlay.point() == (12, 7)


def test_escape_cancels(make, qtbot):
    overlay = make()

    with qtbot.waitSignal(overlay.cancelled):
        QApplication.sendEvent(overlay, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, PLAIN))


def test_pixels_of_a_capture_shown_scaled(make):
    overlay = make(shown=QRectF(0, 25, 200, 50), image=capture(400, 100))  # half size

    drag(overlay, (10.5, 30.5), (50.5, 40.5))

    assert overlay.region() == Region(21, 11, 102, 32)


def test_paints_in_every_state(make):
    overlay = make()
    overlay.show_number(2)
    mouse(overlay, QEvent.Type.MouseButtonPress, 10.5, 20.5, LEFT, LEFT)
    mouse(overlay, QEvent.Type.MouseMove, 50.5, 30.5, NONE, LEFT)

    assert not overlay.grab().isNull()
