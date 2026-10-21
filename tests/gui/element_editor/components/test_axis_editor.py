import pytest
from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox

from guimauve.gui.element_editor_next.components import NOT_SET, AxisEditor, AxisMode, AxisPosition
from guimauve.gui.element_editor_next.schema import FIELDS


@pytest.fixture
def editor(qtbot):
    editor = AxisEditor(FIELDS["x"])
    qtbot.addWidget(editor)
    editor.show()
    editor.emitted = []
    editor.edited.connect(editor.emitted.append)
    return editor


def segment(editor, label: str) -> QPushButton:
    return next(button for button in editor.findChildren(QPushButton) if button.text() == label)


def box(editor) -> QSpinBox:
    """The number box shown, the one of the current mode."""
    return next(box for box in editor.findChildren(QSpinBox) if box.isVisible())


def suffix(editor) -> str:
    return next(label.text() for label in editor.findChildren(QLabel) if label.property("muted"))


def test_not_set_hides_the_number(editor):
    editor.set_value(NOT_SET, False, None)

    assert not any(spin.isVisible() for spin in editor.findChildren(QSpinBox))


@pytest.mark.parametrize(
    ("mode", "text"), [(AxisMode.ABSOLUTE, "px on screen"), (AxisMode.FROM_MOUSE, "px from mouse")]
)
def test_a_mode_shows_its_number_and_suffix(editor, mode, text):
    editor.set_value(AxisPosition(mode, 24), True, None)

    assert box(editor).value() == 24
    assert suffix(editor) == text


def test_another_mode_starts_at_zero(editor):
    editor.set_value(AxisPosition(AxisMode.ABSOLUTE, 1280), True, None)

    segment(editor, "From mouse").click()

    assert editor.emitted == [AxisPosition(AxisMode.FROM_MOUSE, 0)]


def test_not_set_is_emitted_as_such(editor):
    editor.set_value(AxisPosition(AxisMode.ABSOLUTE, 1280), True, None)

    segment(editor, "Not set").click()

    assert editor.emitted == [NOT_SET]


def test_inherited_mode_chosen_again_keeps_its_amount(editor):
    editor.set_value(AxisPosition(AxisMode.ABSOLUTE, 1280), False, None)

    segment(editor, "Absolute").click()

    assert editor.emitted == [AxisPosition(AxisMode.ABSOLUTE, 1280)]


def test_typed_amount_is_emitted_with_the_mode(editor):
    editor.set_value(AxisPosition(AxisMode.FROM_MOUSE, 0), True, None)

    box(editor).setValue(-10)

    assert editor.emitted == [AxisPosition(AxisMode.FROM_MOUSE, -10)]


def test_absolute_position_on_a_screen_is_never_typed_negative(editor):
    editor.set_value(AxisPosition(AxisMode.ABSOLUTE, 5), True, None)

    assert box(editor).minimum() == 0


def test_negative_position_already_set_stays_shown(editor):
    editor.set_value(AxisPosition(AxisMode.ABSOLUTE, -1270), True, None)

    assert box(editor).value() == -1270


def test_negative_position_from_the_primary_screen(editor):
    editor.set_negative_allowed(True)
    editor.set_value(AxisPosition(AxisMode.ABSOLUTE, 5), True, None)

    box(editor).setValue(-1270)

    assert editor.emitted == [AxisPosition(AxisMode.ABSOLUTE, -1270)]


def test_showing_a_value_emits_nothing(editor):
    editor.set_value(AxisPosition(AxisMode.ABSOLUTE, 5), True, None)
    editor.set_negative_allowed(True)
    editor.set_value(NOT_SET, False, None)

    assert editor.emitted == []
