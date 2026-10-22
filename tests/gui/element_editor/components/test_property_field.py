import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox, QToolButton

from guimauve.enums import MouseDirection
from guimauve.gui.element_editor_next.components import BoolEditor, FieldState, NumberEditor, PropertyField
from guimauve.gui.element_editor_next.schema import FIELDS
from guimauve.gui.element_editor_next.state import Source
from guimauve.gui.element_editor_next.theme import METRICS
from guimauve.models.area import Area


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


def tags(field) -> list[str]:
    """Visible tags beside the label."""
    return [label.text() for label in field.findChildren(QLabel) if label.property("tag") and not label.isHidden()]


def message(field) -> QLabel:
    return field.findChild(QLabel, "message")


def code(field) -> QLabel:
    return next(label for label in field.findChildren(QLabel) if label.property("codeValue"))


def test_inherited_value_is_muted_without_tag(make_field):
    field = make_field()
    field.set_state(FieldState(5, inherited=5, source=Source.DEFAULT))
    assert field.findChild(QSpinBox).property("inherited") is True
    assert tags(field) == []
    assert reset(field).isHidden()
    assert code(field).isHidden()


def test_label_tooltip_tells_the_origin(make_field):
    field = make_field()
    field.set_state(FieldState(5, inherited=5, source=Source.DEFAULT))
    label = next(label for label in field.findChildren(QLabel) if label.property("fieldLabel"))
    assert label.toolTip() == "Default value, from the configuration file"


def test_own_value_has_a_reset_that_says_where_it_leads(qtbot, make_field):
    field = make_field()
    field.set_state(FieldState(3, own=True, inherited=5, source=Source.ELEMENT))
    assert not reset(field).isHidden()
    assert reset(field).toolTip() == "Reset to 5 (element)"
    assert tags(field) == []
    with qtbot.waitSignal(field.reset_requested):
        qtbot.mouseClick(reset(field), Qt.MouseButton.LeftButton)


def test_trial_is_tagged(make_field):
    field = make_field()
    field.set_state(FieldState(3, own=True, trial=True, inherited=5, source=Source.DEFAULT))
    assert tags(field) == ["trial"]


def test_code_value_beside_the_label_over_an_own_value(make_field):
    field = make_field()
    field.set_state(FieldState(3, own=True, inherited=5, source=Source.DEFAULT, code=8))
    assert code(field).text() == "{8}"
    assert not code(field).isHidden()
    assert message(field).isHidden()


def test_code_value_beside_the_label_when_inherited(make_field):
    field = make_field()
    field.set_state(FieldState(5, inherited=5, source=Source.DEFAULT, code=8))
    assert code(field).text() == "{8}"
    assert tags(field) == []


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
    field.set_state(FieldState(False, inherited=False, source=Source.DEFAULT))
    values: list = []
    field.edited.connect(values.append)
    on = next(button for button in field.findChildren(QPushButton) if button.text() == "On")
    qtbot.mouseClick(on, Qt.MouseButton.LeftButton)
    assert values == [True]


def test_set_state_emits_nothing(make_field):
    field = make_field()
    emitted: list = []
    field.edited.connect(emitted.append)
    field.reset_requested.connect(lambda: emitted.append("reset"))
    field.set_state(FieldState(7, own=True, inherited=5, source=Source.DEFAULT))
    assert emitted == []


def test_code_area_is_summed_up_beside_the_label(make_field):
    field = make_field("search_area", NumberEditor((0, None), is_float=False))
    area = Area(left=120, top=80, right=760, bottom=440)
    field.set_state(FieldState(None, code=area))
    field.set_label_width(400)  # room for all of it, whatever the font
    assert code(field).text() == "{custom}"
    assert code(field).toolTip() == "Value set in the code for this call: x 120, y 80, 640 × 360"


@pytest.mark.parametrize(("key", "below"), [("x", True), ("timeout", False)])
def test_wide_editor_under_its_label(make_field, key, below):
    field = make_field(key)
    field.resize(360, field.sizeHint().height())
    label = next(label for label in field.findChildren(QLabel) if label.text() == FIELDS[key].label)

    editor_top = field.editor.mapTo(field, field.editor.rect().topLeft()).y()

    assert (editor_top >= label.mapTo(field, label.rect().bottomLeft()).y()) is below


def label(field) -> QLabel:
    return next(label for label in field.findChildren(QLabel) if label.property("fieldLabel"))


def label_text(field) -> str:
    return label(field).text()


def test_label_and_code_fit_the_column(make_field):
    field = make_field("mouse_direction", NumberEditor((0, None), is_float=False))
    field.set_state(FieldState(None, code=MouseDirection.XY_Y))

    field.set_label_width(METRICS.label_width)
    assert code(field).text().endswith("…") and label_text(field).endswith("…")
    assert "Direction" in label(field).toolTip()

    field.set_label_width(400)
    assert (label_text(field), code(field).text()) == ("Direction", "{Y then X}")
    assert "Direction" not in label(field).toolTip()


def test_label_of_several_words_wraps(make_field):
    field = make_field("search_area", NumberEditor((0, None), is_float=False))
    metrics = label(field).fontMetrics()
    one_line = METRICS.dot + METRICS.space(1) + metrics.horizontalAdvance("Search area")

    field.set_label_width(one_line - 1)

    assert label_text(field) == "Search\narea"
