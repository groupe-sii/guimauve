import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox, QToolButton

from guimauve.gui.element_editor_next.components import BoolEditor, FieldState, IconLabel, NumberEditor, PropertyField
from guimauve.gui.element_editor_next.schema import FIELDS
from guimauve.gui.element_editor_next.state import Source


@pytest.fixture
def make_field(qtbot, theme):
    def make(key: str = "timeout", editor=None) -> PropertyField:
        field = PropertyField(FIELDS[key], editor or NumberEditor((0, None), is_float=False), theme)
        qtbot.addWidget(field)
        field.show()
        return field

    return make


def reset(field) -> QToolButton:
    return field.findChild(QToolButton, "reset")


def tag(field) -> QLabel:
    return next(label for label in field.findChildren(QLabel) if label.property("tag"))


def message(field) -> QLabel:
    return next(label for label in field.findChildren(QLabel) if label.wordWrap())


def braces(field) -> IconLabel:
    return field.findChild(IconLabel)


def test_inherited_value_shows_its_source(make_field):
    field = make_field()
    field.set_state(FieldState(5, inherited=5, source=Source.DEFAULT))
    assert tag(field).text() == "default"
    assert reset(field).isHidden()
    assert braces(field).isHidden()


def test_own_value_has_a_reset(qtbot, make_field):
    field = make_field()
    field.set_state(FieldState(3, own=True, inherited=5))
    assert not reset(field).isHidden()
    assert tag(field).isHidden()
    with qtbot.waitSignal(field.reset_requested):
        qtbot.mouseClick(reset(field), Qt.MouseButton.LeftButton)


def test_trial_is_tagged(make_field):
    field = make_field()
    field.set_state(FieldState(3, own=True, trial=True, inherited=5))
    assert tag(field).text() == "trial"


def test_code_over_the_own_value(make_field):
    field = make_field()
    field.set_state(FieldState(3, own=True, inherited=8, code=8))
    assert not braces(field).isHidden()
    assert message(field).text() == "8 in code for this call"
    assert message(field).property("message") == "note"


def test_inherited_from_the_code(make_field):
    field = make_field()
    field.set_state(FieldState(8, inherited=8, source=Source.CODE))
    assert not braces(field).isHidden()
    assert tag(field).text() == "in code"


def test_error_marks_the_input(make_field):
    field = make_field()
    field.set_state(FieldState(3, own=True, error="Must be at least 0"))
    assert message(field).text() == "Must be at least 0"
    assert message(field).property("message") == "error"
    assert field.findChild(QSpinBox).property("invalid") is True


def test_no_effect_disables_with_a_reason(make_field):
    field = make_field("find_all", BoolEditor())
    field.set_state(FieldState(None, disabled_reason="No effect while a fixed position is set"))
    assert not field.isEnabled()
    assert field.toolTip() == "No effect while a fixed position is set"


def test_edits_are_forwarded(qtbot, make_field):
    field = make_field("find_all", BoolEditor())
    field.set_state(FieldState(None, inherited=False, source=Source.DEFAULT))
    values: list = []
    field.edited.connect(values.append)
    on = next(button for button in field.findChildren(QPushButton) if button.text() == "On")
    qtbot.mouseClick(on, Qt.MouseButton.LeftButton)
    assert values == [True]


def test_default_on_a_boolean_is_a_reset(qtbot, make_field):
    field = make_field("find_all", BoolEditor())
    field.set_state(FieldState(True, own=True, inherited=False))
    default = next(button for button in field.findChildren(QPushButton) if button.text().startswith("Default"))
    with qtbot.waitSignal(field.reset_requested):
        qtbot.mouseClick(default, Qt.MouseButton.LeftButton)


def test_set_state_emits_nothing(make_field):
    field = make_field()
    emitted: list = []
    field.edited.connect(emitted.append)
    field.reset_requested.connect(lambda: emitted.append("reset"))
    field.set_state(FieldState(7, own=True, inherited=5))
    assert emitted == []
