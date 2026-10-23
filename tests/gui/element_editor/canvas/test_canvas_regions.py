import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.canvas import CanvasView, Region, TargetMarker, Tool
from guimauve.gui.element_editor_next.services.images import to_qimage

LEFT, NONE = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton


@pytest.fixture
def view(theme, qtbot):
    widget = CanvasView(theme)
    qtbot.addWidget(widget)
    widget.resize(600, 400)
    widget.show()
    widget.set_image(to_qimage(np.zeros((50, 100, 3), np.uint8)))
    return widget


def at(view, x: float, y: float) -> QPointF:
    return view.viewportTransform().map(QPointF(x, y))


def mouse(view, kind, point, button=NONE, buttons=NONE) -> None:
    globally = view.viewport().mapToGlobal(point)
    QApplication.sendEvent(
        view.viewport(), QMouseEvent(kind, point, globally, button, buttons, Qt.KeyboardModifier.NoModifier)
    )


def drag(view, start: QPointF, end: QPointF) -> None:
    mouse(view, QEvent.Type.MouseButtonPress, start, LEFT, LEFT)
    mouse(view, QEvent.Type.MouseMove, end, NONE, LEFT)
    mouse(view, QEvent.Type.MouseButtonRelease, end, LEFT, NONE)


def key(view, code) -> None:
    QApplication.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, code, Qt.KeyboardModifier.NoModifier))


def test_match_area_tool_starts_on_the_whole_image(view, qtbot):
    with qtbot.waitSignal(view.region_changed):
        view.set_tool(Tool.MATCH_AREA)

    assert view.region() == Region(0, 0, 100, 50)
    assert view.region_rect() is not None


def test_no_rectangle_without_image(theme, qtbot):
    view = CanvasView(theme)
    qtbot.addWidget(view)

    view.set_tool(Tool.MATCH_AREA)

    assert view.tool is Tool.SELECT
    assert view.region() is None


def test_m_key_opens_the_match_area_tool(view):
    key(view, Qt.Key.Key_M)

    assert view.tool is Tool.MATCH_AREA


def test_set_region_only_while_editing(view):
    view.set_region(Region(1, 1, 5, 5))
    assert view.region() is None

    view.set_tool(Tool.MATCH_AREA)
    view.set_region(Region(1, 1, 5, 5))
    assert view.region() == Region(1, 1, 5, 5)


def test_drag_a_handle(view):
    view.set_tool(Tool.MATCH_AREA)
    view.set_region(Region(10, 10, 50, 40))

    drag(view, at(view, 50, 40), at(view, 70.2, 44.6))

    assert view.region() == Region(10, 10, 70, 45)


def test_drag_inside_moves(view):
    view.set_tool(Tool.MATCH_AREA)
    view.set_region(Region(10, 10, 50, 40))

    drag(view, at(view, 30, 25), at(view, 35, 20))

    assert view.region() == Region(15, 5, 55, 35)


def test_drag_outside_draws_anew(view):
    view.set_tool(Tool.MATCH_AREA)
    view.set_region(Region(10, 10, 20, 20))

    drag(view, at(view, 60.5, 30.5), at(view, 80.5, 45.5))

    assert view.region() == Region(60, 30, 81, 46)


def test_targets_are_not_handled_while_editing(view, qtbot):
    view.set_targets([TargetMarker(7, 1, None, 30, 25)])
    view.set_tool(Tool.MATCH_AREA)

    with qtbot.assertNotEmitted(view.target_pressed):
        drag(view, at(view, 30.5, 25.5), at(view, 30.5, 25.5))


def test_enter_confirms(view, qtbot):
    view.set_tool(Tool.MATCH_AREA)

    with qtbot.waitSignal(view.region_confirmed):
        key(view, Qt.Key.Key_Return)


def test_escape_drops_the_rectangle(view):
    view.set_tool(Tool.MATCH_AREA)

    key(view, Qt.Key.Key_Escape)

    assert view.tool is Tool.SELECT
    assert view.region() is None


def test_a_new_image_drops_the_rectangle(view):
    view.set_tool(Tool.MATCH_AREA)

    view.set_image(to_qimage(np.zeros((10, 10, 3), np.uint8)))

    assert view.tool is Tool.SELECT
    assert view.region() is None
