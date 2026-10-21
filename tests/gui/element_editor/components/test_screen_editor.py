import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QToolButton

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.components import ScreenEditor, ScreenPills, screen_label

SCREENS = [Screen(-1280, 0, 3200, 1080), Screen(0, 0, 1920, 1080), Screen(-1280, 0, 1280, 1024)]


@pytest.fixture
def editor(qtbot, theme):
    editor = ScreenEditor(theme)
    qtbot.addWidget(editor)
    editor.set_screens(SCREENS)
    editor.show()
    editor.emitted = []
    editor.edited.connect(editor.emitted.append)
    return editor


def combo(editor) -> QComboBox:
    return editor.findChild(QComboBox)


def labels(editor) -> list[str]:
    return [combo(editor).itemText(index) for index in range(combo(editor).count())]


def choose(editor, label: str) -> None:
    index = labels(editor).index(label)
    combo(editor).setCurrentIndex(index)
    combo(editor).activated.emit(index)


def pills(editor) -> ScreenPills:
    return editor.findChild(ScreenPills)


def shown_pills(editor) -> list[QFrame]:
    return [pill for pill in pills(editor).findChildren(QFrame) if pill.property("screenPill") and not pill.isHidden()]


def removes(editor) -> list[QToolButton]:
    return [b for pill in shown_pills(editor) for b in pill.findChildren(QToolButton) if b.isVisible()]


def add_button(editor) -> QToolButton:
    return next(button for button in pills(editor).findChildren(QToolButton) if button.menu() is not None)


def test_screens_of_the_driver_are_offered(editor):
    editor.set_value(1, False, 1)

    assert labels(editor) == ["All screens", "", "1 · Primary · 1920 × 1080", "2 · 1280 × 1024", "", "Multiple…"]
    assert combo(editor).currentText() == "1 · Primary · 1920 × 1080"


def test_a_missing_screen_keeps_its_entry(editor):
    editor.set_value(3, True, 1)

    assert combo(editor).currentText() == "3 · Not connected"


def test_screens_unknown_with_vnc(qtbot, theme):
    editor = ScreenEditor(theme)
    qtbot.addWidget(editor)
    editor.set_value(2, True, 1)

    assert combo(editor).currentText() == "Screen 2"


@pytest.mark.parametrize(("value", "started"), [(2, [2]), (0, [1])])
def test_multiple_starts_with_the_current_screen(editor, value, started):
    editor.set_value(value, True, 1)

    choose(editor, "Multiple…")

    assert editor.emitted == [started]


def test_a_list_shows_its_pills(editor):
    editor.set_value([2, 1], True, 1)

    assert combo(editor).currentText() == "Multiple screens"
    assert [pill.toolTip() for pill in shown_pills(editor)] == [
        screen_label(2, tuple(SCREENS)),
        screen_label(1, tuple(SCREENS)),
    ]


def test_a_single_screen_hides_the_pills(editor):
    editor.set_value([2, 1], True, 1)
    editor.set_value(1, True, 1)

    assert not pills(editor).isVisible()


def test_cross_removes_a_screen(editor):
    editor.set_value([2, 1], True, 1)

    removes(editor)[0].click()

    assert editor.emitted == [[1]]


def test_last_screen_cannot_be_removed(editor):
    editor.set_value([2], True, 1)

    assert removes(editor) == []


def test_add_offers_the_screens_not_in_the_list(editor):
    editor.set_value([2], True, 1)
    (action,) = add_button(editor).menu().actions()

    action.trigger()

    assert action.text() == "1 · Primary · 1920 × 1080"
    assert editor.emitted == [[2, 1]]


def test_add_is_hidden_when_every_screen_is_listed(editor):
    editor.set_value([2, 1], True, 1)

    assert not add_button(editor).isVisible()


def test_alt_arrow_moves_a_screen_and_keeps_the_focus(editor, qtbot):
    editor.set_value([2, 1], True, 1)
    editor.edited.connect(lambda numbers: editor.set_value(numbers, True, 1))  # as the store would
    first = shown_pills(editor)[0]
    first.setFocus()

    qtbot.keyClick(first, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)

    assert editor.emitted == [[1, 2]]
    assert pills(editor).focusWidget() is shown_pills(editor)[1]


def test_move_keeps_the_screen_in_the_list(editor):
    editor.set_value([2, 1], True, 1)

    pills(editor).move_screen(1, 0)
    pills(editor).move_screen(0, 5)

    assert editor.emitted == [[1, 2], [1, 2]]
