import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
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


def test_ctrl_holds_the_target_tool(view):
    key(view, Qt.Key.Key_Control, modifiers=CTRL)
    assert view.tool is Tool.TARGET

    key(view, Qt.Key.Key_Control, QEvent.Type.KeyRelease)
    assert view.tool is Tool.SELECT


def test_ctrl_seen_on_mouse_moves(view):
    mouse(view, QEvent.Type.MouseMove, at(view, 10, 10), modifiers=CTRL)
    assert view.tool is Tool.TARGET

    mouse(view, QEvent.Type.MouseMove, at(view, 10, 10))
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


def test_ctrl_click_adds_a_target(view, qtbot):
    with qtbot.waitSignal(view.target_added), qtbot.assertNotEmitted(view.background_clicked):
        click(view, at(view, 30.5, 12.5), CTRL)


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
    assert not toolbar.button(Tool.MATCH_AREA).isEnabled()
    assert not toolbar.button(Tool.CROP).isEnabled()
    assert "(T)" in toolbar.button(Tool.TARGET).toolTip()
    with qtbot.waitSignal(toolbar.tool_chosen) as chosen:
        toolbar.button(Tool.SELECT).click()
    assert chosen.args == [Tool.SELECT]


def wheel(view, point: QPointF, modifiers=PLAIN) -> None:
    globally = view.viewport().mapToGlobal(point)
    event = QWheelEvent(point, globally, QPoint(), QPoint(0, 120), NONE, modifiers, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(view.viewport(), event)


def test_ctrl_with_the_wheel_zooms_without_the_target_tool(view):
    """A pinch on a Windows touchpad is Ctrl held with the wheel."""
    key(view, Qt.Key.Key_Control, modifiers=CTRL)
    zoom = view.zoom

    wheel(view, at(view, 10, 10), CTRL)
    mouse(view, QEvent.Type.MouseMove, at(view, 10, 10), modifiers=CTRL)

    assert view.zoom > zoom
    assert view.tool is Tool.SELECT
    assert not view.shows_magnifier()


def test_ctrl_holds_the_target_tool_again_once_released(view):
    wheel(view, at(view, 10, 10), CTRL)
    key(view, Qt.Key.Key_Control, QEvent.Type.KeyRelease)

    key(view, Qt.Key.Key_Control, modifiers=CTRL)

    assert view.tool is Tool.TARGET
