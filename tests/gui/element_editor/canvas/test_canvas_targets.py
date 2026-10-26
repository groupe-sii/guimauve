import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.canvas import CanvasView, TargetMarker
from guimauve.gui.element_editor_next.services.images import to_qimage

LEFT, NONE = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton


@pytest.fixture
def view(theme, qtbot):
    widget = CanvasView(theme)
    qtbot.addWidget(widget)
    widget.resize(600, 400)
    widget.show()
    widget.set_image(to_qimage(np.zeros((50, 100, 3), np.uint8)))  # fitted at 200 %
    return widget


def at(view, x: float, y: float) -> QPointF:
    """Point of the viewport over a point of the image."""
    return view.viewportTransform().map(QPointF(x, y))


def mouse(view, kind, point: QPointF, button=NONE, buttons=NONE) -> None:
    globally = view.viewport().mapToGlobal(point)
    QApplication.sendEvent(
        view.viewport(), QMouseEvent(kind, point, globally, button, buttons, Qt.KeyboardModifier.NoModifier)
    )


def press(view, point):
    mouse(view, QEvent.Type.MouseButtonPress, point, LEFT, LEFT)


def move(view, point):
    mouse(view, QEvent.Type.MouseMove, point, NONE, LEFT)


def release(view, point):
    mouse(view, QEvent.Type.MouseButtonRelease, point, LEFT, NONE)


def key(view, code, modifiers=Qt.KeyboardModifier.NoModifier) -> None:
    QApplication.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, code, modifiers))


def test_targets_are_added_updated_and_removed(view):
    view.set_targets([TargetMarker(1, 1, "a", 10, 10), TargetMarker(2, 2, None, 30, 20)])
    first = {item.marker.key: item for item in view.target_items()}[1]

    view.set_targets([TargetMarker(1, 1, "a", 12, 10, selected=True)])

    assert view.target_items() == [first]
    assert first.marker.x == 12
    assert first.pos() == QPointF(12.5, 10.5)  # centre of the pixel
    assert first.zValue() > 1  # a selected target is on top


def test_target_at(view):
    view.set_targets([TargetMarker(7, 1, None, 10, 10)])

    assert view.target_at(at(view, 10.5, 10.5)) == 7
    assert view.target_at(at(view, 40, 40)) is None


def test_name_shows_on_selection_only(view):
    view.set_targets([TargetMarker(1, 1, "a", 10, 10), TargetMarker(2, 2, "b", 30, 30, selected=True)])

    shown = {item.marker.key: item.shows_name() for item in view.target_items()}

    assert shown == {1: False, 2: True}


def test_drag_a_target_pixel_by_pixel(view, qtbot):
    view.set_targets([TargetMarker(7, 1, None, 10, 10)])
    dragged = []
    view.target_dragged.connect(lambda *args: dragged.append(args))

    with qtbot.waitSignal(view.target_pressed) as pressed:
        press(view, at(view, 10.8, 10.2))  # grabbed off the centre of its pixel: the offset is kept
    move(view, at(view, 20.8, 15.2))
    with qtbot.waitSignal(view.target_released):
        release(view, at(view, 20.8, 15.2))

    assert pressed.args == [7]
    assert dragged[-1] == (7, 20, 15)


def test_click_on_a_target_does_not_move_it(view, qtbot):
    view.set_targets([TargetMarker(7, 1, None, 10, 10)])
    dragged = []
    view.target_dragged.connect(lambda *args: dragged.append(args))

    with qtbot.waitSignal(view.target_released):
        press(view, at(view, 10.5, 10.5))
        release(view, at(view, 10.5, 10.5))

    assert dragged == []


def test_a_target_can_be_dragged_out_of_the_image(view):
    view.set_targets([TargetMarker(7, 1, None, 1, 1)])
    dragged = []
    view.target_dragged.connect(lambda *args: dragged.append(args))

    press(view, at(view, 1.5, 1.5))
    move(view, at(view, -3.5, 1.5))

    assert dragged[-1] == (7, -4, 1)


def test_click_on_the_background(view, qtbot):
    with qtbot.waitSignal(view.background_clicked):
        press(view, at(view, 40, 40))
        release(view, at(view, 40, 40))


def test_drag_of_the_background_is_no_click(view, qtbot):
    view.set_zoom(4.0)

    with qtbot.assertNotEmitted(view.background_clicked):
        press(view, at(view, 40, 40))
        move(view, at(view, 30, 30))
        release(view, at(view, 30, 30))


@pytest.mark.parametrize(
    ("code", "modifiers", "expected"),
    [
        (Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier, [-1, 0]),
        (Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier, [0, 1]),
        (Qt.Key.Key_Up, Qt.KeyboardModifier.ShiftModifier, [0, -10]),
    ],
)
def test_arrows_nudge(view, qtbot, code, modifiers, expected):
    with qtbot.waitSignal(view.nudge_requested) as nudged:
        key(view, code, modifiers)

    assert nudged.args == expected


@pytest.mark.parametrize("code", [Qt.Key.Key_Delete, Qt.Key.Key_Backspace])
def test_delete_keys(view, qtbot, code):
    with qtbot.waitSignal(view.delete_requested):
        key(view, code)
