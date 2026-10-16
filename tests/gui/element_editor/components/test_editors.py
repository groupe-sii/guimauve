import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QPushButton, QSlider, QSpinBox

from guimauve.enums import MouseDirection, OcrFidelity
from guimauve.gui.element_editor_next.components import (
    BoolEditor,
    EnumEditor,
    NumberEditor,
    SwitchEditor,
    editor_for,
    label_of,
)
from guimauve.gui.element_editor_next.schema import FIELDS


@pytest.fixture
def record(qtbot):
    """Shows the editor and returns the list of the values it emits."""

    def start(editor):
        qtbot.addWidget(editor)
        editor.show()
        values: list = []
        editor.edited.connect(values.append)
        return values

    return start


def segment(editor, label: str) -> QPushButton:
    return next(button for button in editor.findChildren(QPushButton) if button.text().startswith(label))


@pytest.mark.parametrize(
    ("key", "kind"),
    [
        ("find_all", BoolEditor),
        ("template_grayscale", BoolEditor),
        ("use_ocr", SwitchEditor),
        ("ocr_fidelity", EnumEditor),
        ("mouse_direction", EnumEditor),
        ("timeout", NumberEditor),
        ("match_index", NumberEditor),
        ("feature_sigma", NumberEditor),
    ],
)
def test_editor_follows_the_type(qtbot, theme, key, kind):
    editor = editor_for(FIELDS[key], theme)
    qtbot.addWidget(editor)
    assert isinstance(editor, kind)


@pytest.mark.parametrize("key", ["target", "screen", "search_area", "x", "rel_y"])
def test_special_fields_have_no_generic_editor(theme, key):
    assert editor_for(FIELDS[key], theme) is None


def test_labels():
    assert [label_of(v) for v in (True, 0.85, MouseDirection.XY_X, OcrFidelity.FAST, 3)] == [
        "on",
        "0.85",
        "X then Y",
        "Fast",
        "3",
    ]


def test_bool_default_shows_the_inherited_value(record):
    editor = BoolEditor()
    record(editor)
    editor.set_value(None, own=False, inherited=False)
    assert segment(editor, "Default").text() == "Default (off)"
    assert segment(editor, "Default").isChecked()


def test_bool_emits_on_click_and_none_for_default(qtbot, record):
    editor = BoolEditor()
    values = record(editor)
    editor.set_value(True, own=True, inherited=False)
    qtbot.mouseClick(segment(editor, "Off"), Qt.MouseButton.LeftButton)
    qtbot.mouseClick(segment(editor, "Default"), Qt.MouseButton.LeftButton)
    assert values == [False, None]


def test_set_value_never_emits(record, theme):
    editors = [BoolEditor(), SwitchEditor(theme), EnumEditor(OcrFidelity), NumberEditor((0, 1), is_float=True)]
    emitted = [record(editor) for editor in editors]
    for editor, value in zip(editors, (True, True, OcrFidelity.ACCURATE, 0.5), strict=True):
        editor.set_value(value, own=True, inherited=None)
    assert emitted == [[], [], [], []]


def test_enum_emits_the_member(qtbot, record):
    editor = EnumEditor(OcrFidelity)
    values = record(editor)
    editor.set_value(OcrFidelity.FAST, own=False, inherited=OcrFidelity.FAST)
    qtbot.mouseClick(segment(editor, "Accurate"), Qt.MouseButton.LeftButton)
    assert values == [OcrFidelity.ACCURATE]


def test_inherited_value_is_muted(record):
    editor = NumberEditor((0, None), is_float=False)
    record(editor)
    editor.set_value(5, own=False, inherited=5)
    assert editor.findChild(QSpinBox).property("inherited") is True
    editor.set_value(5, own=True, inherited=3)
    assert editor.findChild(QSpinBox).property("inherited") is False


def test_number_is_bounded_by_pydantic(qtbot, theme):
    editor = editor_for(FIELDS["feature_sigma"], theme)
    qtbot.addWidget(editor)
    box = editor.findChild(QDoubleSpinBox)
    assert (box.minimum(), box.maximum()) == (0.5, 3.0)


def test_typed_number_is_sent_on_enter(qtbot, record):
    editor = NumberEditor((0, 5000), is_float=False)
    values = record(editor)
    box = editor.findChild(QSpinBox)
    box.lineEdit().selectAll()
    qtbot.keyClicks(box, "250")
    assert values == []
    qtbot.keyClick(box, Qt.Key.Key_Return)
    assert values == [250]


def test_decimal_separator_is_a_dot(record):
    editor = NumberEditor((0, 10), is_float=True)
    record(editor)
    editor.set_value(1.5, own=True, inherited=None)
    assert editor.findChild(QDoubleSpinBox).text() == "1.50"


def test_threshold_slider_starts_a_gesture(qtbot, record):
    editor = NumberEditor((0, 1), is_float=True)
    values = record(editor)
    slider = editor.findChild(QSlider)
    with qtbot.waitSignal(editor.edit_started):
        slider.sliderPressed.emit()
    slider.setValue(80)
    assert values == [0.8]
    assert editor.findChild(QDoubleSpinBox).value() == 0.8


def test_other_numbers_have_no_slider(record):
    editor = NumberEditor((0, 5000), is_float=False)
    record(editor)
    assert editor.findChild(QSlider) is None


def wheel() -> QWheelEvent:
    return QWheelEvent(
        QPointF(5, 5),
        QPointF(5, 5),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )


@pytest.mark.parametrize("kind", [QDoubleSpinBox, QSlider])
def test_wheel_never_changes_a_value(record, kind):
    editor = NumberEditor((0, 1), is_float=True)
    values = record(editor)
    editor.set_value(0.5, own=True, inherited=None)
    target = editor.findChild(kind)
    target.setFocus()
    event = wheel()
    QApplication.sendEvent(target, event)
    assert values == []
    assert not event.isAccepted()  # left to the scroll area of the inspector
