import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import SegmentedControl
from guimauve.gui.element_editor_next.components.restyle import set_style_property


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


def test_reselectable_emits_on_the_selected_segment(qtbot, control, activated):
    control.set_reselectable(True)
    qtbot.mouseClick(segment(control, 0), Qt.MouseButton.LeftButton)
    assert activated == [None]


@pytest.fixture
def focusable(qtbot):
    """A control after a field that holds the focus first, in an active window."""
    host = QWidget()
    qtbot.addWidget(host)
    layout = QVBoxLayout(host)
    field = QLineEdit()
    control = SegmentedControl([(True, "On"), (False, "Off")])
    layout.addWidget(field)
    layout.addWidget(control)
    host.show()
    host.activateWindow()
    qtbot.waitUntil(host.isActiveWindow)
    field.setFocus()
    yield control  # the host stays alive meanwhile


@pytest.mark.parametrize(
    ("reason", "shown"),
    [
        (Qt.FocusReason.TabFocusReason, True),
        (Qt.FocusReason.BacktabFocusReason, True),
        (Qt.FocusReason.MouseFocusReason, False),
    ],
)
def test_focus_shows_only_from_the_keyboard(focusable, reason, shown):
    focusable.setFocus(reason)

    assert focusable.hasFocus()
    assert bool(focusable.property("keyboardFocus")) is shown


def test_focus_from_the_keyboard_stays_shown_back_to_the_window(focusable):
    focusable.setFocus(Qt.FocusReason.TabFocusReason)

    QApplication.sendEvent(focusable, QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.ActiveWindowFocusReason))

    assert focusable.property("keyboardFocus") is True


def test_the_pill_sits_under_the_value_chosen(control, qtbot):
    control.set_value(False)

    qtbot.waitUntil(lambda: control.thumb.geometry() == segment(control, 2).geometry())


def test_the_pill_slides_to_a_value_clicked(control, qtbot):
    qtbot.waitUntil(lambda: control.thumb.geometry() == segment(control, 0).geometry())

    segment(control, 2).click()

    assert control.thumb.geometry() != segment(control, 2).geometry()  # on its way
    qtbot.waitUntil(lambda: control.thumb.geometry() == segment(control, 2).geometry())


def test_the_pill_keeps_sliding_when_the_value_comes_back(control, qtbot):
    control.activated.connect(control.set_value)  # as a field does, through the store
    qtbot.waitUntil(lambda: control.thumb.geometry() == segment(control, 0).geometry())

    segment(control, 2).click()

    assert control.thumb.geometry() != segment(control, 2).geometry()  # still on its way
    qtbot.waitUntil(lambda: control.thumb.geometry() == segment(control, 2).geometry())


def test_an_inherited_value_has_no_pill(control):
    set_style_property(control, "inherited", True)
    assert control.thumb.isHidden()

    set_style_property(control, "inherited", False)
    assert not control.thumb.isHidden()


def test_the_pill_of_an_accent_value(control):
    control.set_accent(False)

    assert control.thumb.property("accent") is False
    control.set_value(False)
    assert control.thumb.property("accent") is True
