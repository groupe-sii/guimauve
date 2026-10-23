import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.canvas import CanvasView, EditToolbar, TargetMarker, Tool
from guimauve.gui.element_editor_next.services.images import to_qimage

LEFT, NONE = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton
CTRL, PLAIN = Qt.KeyboardModifier.ControlModifier, Qt.KeyboardModifier.NoModifier


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


def mouse(view, kind, point, button=NONE, buttons=NONE, modifiers=PLAIN) -> None:
    globally = view.viewport().mapToGlobal(point)
    QApplication.sendEvent(view.viewport(), QMouseEvent(kind, point, globally, button, buttons, modifiers))


def click(view, point, modifiers=PLAIN) -> None:
    mouse(view, QEvent.Type.MouseButtonPress, point, LEFT, LEFT, modifiers)
    mouse(view, QEvent.Type.MouseButtonRelease, point, LEFT, NONE, modifiers)


def key(view, code, kind=QEvent.Type.KeyPress, modifiers=PLAIN) -> None:
    QApplication.sendEvent(view, QKeyEvent(kind, code, modifiers))


def test_starts_with_select(view):
    assert view.tool is Tool.SELECT


def test_set_tool(view, qtbot):
    with qtbot.waitSignal(view.tool_changed):
        view.set_tool(Tool.TARGET)

    assert view.tool is Tool.TARGET


@pytest.mark.parametrize(("code", "expected"), [(Qt.Key.Key_T, Tool.TARGET), (Qt.Key.Key_V, Tool.SELECT)])
def test_tool_keys(view, code, expected):
    view.set_tool(Tool.TARGET if expected is Tool.SELECT else Tool.SELECT)

    key(view, code)

    assert view.tool is expected


def test_escape_goes_back_to_select(view):
    view.set_tool(Tool.TARGET)

    key(view, Qt.Key.Key_Escape)

    assert view.tool is Tool.SELECT


def test_click_in_the_target_tool_adds_a_target(view, qtbot):
    view.set_tool(Tool.TARGET)

    with qtbot.waitSignal(view.target_added) as added:
        click(view, at(view, 30.7, 12.2))

    assert added.args == [30, 12]


def test_target_can_be_added_outside_the_image(view, qtbot):
    view.set_tool(Tool.TARGET)

    with qtbot.waitSignal(view.target_added) as added:
        click(view, at(view, -2.5, 10.5))

    assert added.args == [-3, 10]


def test_click_on_a_target_in_the_target_tool_selects_it(view, qtbot):
    view.set_targets([TargetMarker(7, 1, None, 30, 12)])
    view.set_tool(Tool.TARGET)

    with qtbot.waitSignal(view.target_pressed), qtbot.assertNotEmitted(view.target_added):
        click(view, at(view, 30.5, 12.5))


def test_magnifier_only_on_the_image_in_the_target_tool(view):
    mouse(view, QEvent.Type.MouseMove, at(view, 30.5, 12.5))
    assert not view.shows_magnifier()

    view.set_tool(Tool.TARGET)
    assert view.shows_magnifier()

    mouse(view, QEvent.Type.MouseMove, at(view, -5, 12.5))
    assert not view.shows_magnifier()


def test_toolbar(theme, qtbot):
    toolbar = EditToolbar(theme)
    qtbot.addWidget(toolbar)

    toolbar.show_tool(Tool.TARGET)

    assert toolbar.button(Tool.TARGET).isChecked()
    assert all(toolbar.button(tool).isEnabled() for tool in Tool)
    assert "(T)" in toolbar.button(Tool.TARGET).toolTip()
    with qtbot.waitSignal(toolbar.tool_chosen) as chosen:
        toolbar.button(Tool.SELECT).click()
    assert chosen.args == [Tool.SELECT]


def press_and_move(view, start: QPointF, end: QPointF) -> None:
    mouse(view, QEvent.Type.MouseButtonPress, start, LEFT, LEFT)
    mouse(view, QEvent.Type.MouseMove, end, NONE, LEFT)


def test_dragging_a_target_aims_at_its_drop_pixel(view):
    view.set_targets([TargetMarker(7, 1, None, 30, 12)])

    press_and_move(view, at(view, 30.5, 12.5), at(view, 40.5, 20.5))

    assert view.aimed_pixel() == QPoint(40, 20)
    assert view.viewport().cursor().shape() == Qt.CursorShape.CrossCursor


def test_no_magnifier_while_a_target_is_dragged_out_of_the_image(view):
    view.set_targets([TargetMarker(7, 1, None, 3, 12)])

    press_and_move(view, at(view, 3.5, 12.5), at(view, -4.5, 12.5))

    assert not view.shows_magnifier()


def test_no_magnifier_while_the_view_moves(view):
    view.set_tool(Tool.TARGET)
    view.set_zoom(4.0)

    press_and_move(view, at(view, 30.5, 12.5), at(view, 20.5, 12.5))

    assert not view.shows_magnifier()


def test_ctrl_does_not_change_the_tool(view, qtbot):
    with qtbot.assertNotEmitted(view.target_added):
        key(view, Qt.Key.Key_Control, modifiers=CTRL)
        click(view, at(view, 30.5, 12.5), CTRL)

    assert view.tool is Tool.SELECT
