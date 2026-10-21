import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox

from guimauve.gui.element_editor_next.components import TargetEditor


@pytest.fixture
def editor(qtbot):
    editor = TargetEditor()
    qtbot.addWidget(editor)
    editor.show()
    editor.emitted = []
    editor.edited.connect(editor.emitted.append)
    return editor


def combo(editor) -> QComboBox:
    return editor.findChild(QComboBox)


def labels(editor) -> list[str]:
    """Labels of the entries; a separator has an empty label."""
    return [combo(editor).itemText(index) for index in range(combo(editor).count())]


def choose(editor, label: str) -> None:
    """Chooses an entry as the user does."""
    index = labels(editor).index(label)
    combo(editor).setCurrentIndex(index)
    combo(editor).activated.emit(index)


def test_default_comes_first_then_the_names(editor):
    editor.set_names(["icon", "arrow"])
    editor.set_value(None, False, None)

    assert labels(editor) == ["Default", "", "icon", "arrow"]
    assert combo(editor).currentText() == "Default"


def test_a_target_named_default_is_not_the_default(editor):
    editor.set_names(["default"])
    editor.set_value(None, False, None)

    choose(editor, "default")

    assert editor.emitted == ["default"]


def test_choosing_default_removes_the_own_value(editor):
    editor.set_names(["icon"])
    editor.set_value("icon", True, None)

    choose(editor, "Default")

    assert editor.emitted == [None]


def test_a_missing_name_keeps_its_entry(editor):
    editor.set_names(["icon"])
    editor.set_value("gone", True, None)

    assert labels(editor) == ["Default", "", "icon", "gone"]
    assert combo(editor).currentText() == "gone"


def test_a_point_is_shown_only_when_set(editor):
    editor.set_value([120, 80], True, None)
    assert combo(editor).currentText() == "Point x 120, y 80"

    editor.set_value(None, False, None)
    assert not any(label.startswith("Point") for label in labels(editor))


def test_choosing_the_own_value_again_emits_nothing(editor):
    editor.set_names(["icon"])
    editor.set_value("icon", True, None)

    choose(editor, "icon")

    assert editor.emitted == []


def test_choosing_the_inherited_value_sets_it(editor):
    editor.set_names(["icon"])
    editor.set_value("icon", False, "icon")

    choose(editor, "icon")

    assert editor.emitted == ["icon"]


def test_showing_a_value_emits_nothing(editor):
    editor.set_names(["icon", "arrow"])
    editor.set_value("arrow", True, None)
    editor.set_names(["arrow"])

    assert editor.emitted == []
    assert combo(editor).currentText() == "arrow"


def test_inherited_value_is_muted(editor):
    editor.set_value(None, False, None)
    assert combo(editor).property("inherited") is True

    editor.set_value("icon", True, None)
    assert combo(editor).property("inherited") is False


def test_wheel_never_changes_the_value(editor):
    editor.set_names(["icon", "arrow"])
    editor.set_value(None, False, None)
    center = QPointF(combo(editor).rect().center())
    wheel = QWheelEvent(
        center,
        QPointF(combo(editor).mapToGlobal(center.toPoint())),
        QPoint(),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    QApplication.sendEvent(combo(editor), wheel)

    assert combo(editor).currentText() == "Default"
    assert editor.emitted == []
