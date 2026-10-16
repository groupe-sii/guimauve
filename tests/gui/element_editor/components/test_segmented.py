import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from guimauve.gui.element_editor_next.components import SegmentedControl


@pytest.fixture
def control(qtbot):
    control = SegmentedControl([(None, "Default"), (True, "On"), (False, "Off")])
    qtbot.addWidget(control)
    control.show()
    return control


@pytest.fixture
def activated(control):
    values: list = []
    control.activated.connect(values.append)
    return values


def segment(control, index) -> QPushButton:
    return control.findChildren(QPushButton)[index]


def test_first_value_is_selected(control):
    assert control.value() is None
    assert segment(control, 0).isChecked()


def test_click_selects_and_emits(qtbot, control, activated):
    qtbot.mouseClick(segment(control, 1), Qt.MouseButton.LeftButton)
    assert control.value() is True
    assert activated == [True]


def test_click_on_the_selected_segment_emits_nothing(qtbot, control, activated):
    qtbot.mouseClick(segment(control, 0), Qt.MouseButton.LeftButton)
    assert activated == []


def test_set_value_emits_nothing(control, activated):
    control.set_value(False)
    assert control.value() is False
    assert segment(control, 2).isChecked()
    assert activated == []


def test_arrows_change_the_value(qtbot, control, activated):
    qtbot.keyClick(control, Qt.Key.Key_Right)
    qtbot.keyClick(control, Qt.Key.Key_Right)
    qtbot.keyClick(control, Qt.Key.Key_Right)  # already the last one
    assert activated == [True, False]


def test_segments_never_take_the_focus(control):
    assert all(button.focusPolicy() is Qt.FocusPolicy.NoFocus for button in control.findChildren(QPushButton))
