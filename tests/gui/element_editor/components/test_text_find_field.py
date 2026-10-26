import pytest
from PySide6.QtCore import QEvent, QKeyCombination, Qt
from PySide6.QtGui import QFocusEvent, QGuiApplication, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import TextFindField
from guimauve.gui.element_editor_next.components.text_find_field import LABEL, one_line
from guimauve.gui.element_editor_next.theme import METRICS

UNDO, REDO = QKeySequence.StandardKey.Undo, QKeySequence.StandardKey.Redo


@pytest.fixture
def field(qtbot, theme):
    field = TextFindField(theme)
    qtbot.addWidget(field)
    return field


def binding(keys: QKeySequence.StandardKey) -> QKeyCombination:
    """First binding of a standard key on this platform."""
    return QKeySequence.keyBindings(keys)[0][0]


def press(widget: QWidget, keys: QKeySequence.StandardKey) -> None:
    """Presses a standard key, straight to the widget: without the shortcuts of the window."""
    combination = binding(keys)
    for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
        QApplication.sendEvent(widget, QKeyEvent(kind, combination.key(), combination.keyboardModifiers()))


def test_label_names_the_field(field):
    label = next(label for label in field.findChildren(QLabel) if label.text() == LABEL)
    assert label.buddy() is field.input


def test_is_never_wider_than_its_token(field):
    assert field.maximumWidth() == field.sizeHint().width() == METRICS.text_find_width
    assert field.input.height() == METRICS.text_find_height


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Sign\nin", "Sign in"), ("Sign\r\nin", "Sign in"), ("Sign\tin", "Sign in"), ("Sign\n\n in", "Sign  in")],
)
def test_line_breaks_and_tabs_become_one_space(text, expected):
    assert one_line(text) == expected


def test_pasted_lines_become_one_line(qtbot, field):
    QGuiApplication.clipboard().setText("Sign in\nwith your account")
    with qtbot.waitSignal(field.edited) as signal:
        field.input.paste()
    assert signal.args == ["Sign in with your account"]
    assert field.text() == "Sign in with your account"


def test_cursor_stays_after_the_same_characters(field):
    field.set_text("Signin")
    field.input.setCursorPosition(4)
    field.input.insert("\r\n")
    assert (field.text(), field.input.cursorPosition()) == ("Sign in", 5)


def test_emits_on_user_edits_only(qtbot, field):
    edits = []
    field.edited.connect(edits.append)
    qtbot.keyClicks(field.input, "ab")
    field.set_text("Sign in")
    assert edits == ["a", "ab"]
    assert field.text() == "Sign in"


def test_set_text_keeps_the_cursor_when_the_text_is_shown(field):
    field.set_text("Sign in")
    field.input.setCursorPosition(2)
    field.set_text("Sign in")
    assert field.input.cursorPosition() == 2


def test_set_text_shows_one_line(field):
    field.set_text("Sign\nin")
    assert field.text() == "Sign in"


def test_enter_finishes_the_edit(qtbot, field):
    with qtbot.waitSignal(field.edit_finished):
        qtbot.keyClick(field.input, Qt.Key.Key_Return)


@pytest.mark.parametrize(
    ("reason", "finished"),
    [
        (Qt.FocusReason.TabFocusReason, True),
        (Qt.FocusReason.MouseFocusReason, True),
        (Qt.FocusReason.ActiveWindowFocusReason, True),
        (Qt.FocusReason.PopupFocusReason, False),
    ],
)
def test_losing_the_focus_finishes_the_edit_except_for_a_menu(field, reason, finished):
    calls = []
    field.edit_finished.connect(lambda: calls.append(True))
    QApplication.sendEvent(field.input, QFocusEvent(QEvent.Type.FocusOut, reason))
    assert bool(calls) is finished


def test_error_shows_a_message_and_a_red_border(field):
    field.set_error("Must not be empty")
    shown = [label for label in field.findChildren(QLabel) if label.text() == "Must not be empty"]
    assert len(shown) == 1 and shown[0].isVisibleTo(field)
    assert field.input.property("invalid") is True

    field.set_error(None)
    assert not shown[0].isVisibleTo(field)
    assert field.input.property("invalid") is False


@pytest.mark.parametrize("keys", [UNDO, REDO])
def test_undo_and_redo_are_left_to_the_window(field, keys):
    combination = binding(keys)
    event = QKeyEvent(QEvent.Type.ShortcutOverride, combination.key(), combination.keyboardModifiers())
    QApplication.sendEvent(field.input, event)
    assert not event.isAccepted()


def test_the_field_keeps_no_history_of_its_own(qtbot, field):
    qtbot.keyClicks(field.input, "ab")
    press(field.input, UNDO)
    assert field.text() == "ab"
    field.input.undo()  # what the field would redo
    undone = field.text()
    press(field.input, REDO)
    assert field.text() == undone


def test_undo_runs_the_shortcut_of_the_window(qtbot, theme):
    window = QWidget()
    qtbot.addWidget(window)
    field = TextFindField(theme)
    QVBoxLayout(window).addWidget(field)
    undone = []
    QShortcut(QKeySequence(UNDO), window, lambda: undone.append(True))
    window.show()
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    field.focus_text()
    qtbot.keyClicks(field.input, "ab")
    combination = binding(UNDO)
    qtbot.keyClick(field.input, combination.key(), combination.keyboardModifiers())
    assert undone == [True]
    assert field.text() == "ab"


def test_context_menu_has_no_undo_nor_redo(qtbot, field):
    field.set_text("Sign in")
    menu = field.input.context_menu()
    qtbot.addWidget(menu)
    names = [action.objectName() for action in menu.actions()]
    assert "edit-undo" not in names and "edit-redo" not in names
    assert "edit-paste" in names
    assert not menu.actions()[0].isSeparator()


def test_focus_text_selects_the_text(field):
    field.set_text("Sign in")
    field.focus_text()
    assert field.input.selectedText() == "Sign in"
