"""Field of the text a text variant looks for: large, on one line, with its error under it."""

import re

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QContextMenuEvent, QFocusEvent, QKeyEvent, QKeySequence, QValidator
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QMenu, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components.badge import CenteredLabel
from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

LABEL = "Text to find"

_NOT_SPACE = re.compile(r"[^\S ]+")  # white space other than the space: line breaks, tabs
_HISTORY = (QKeySequence.StandardKey.Undo, QKeySequence.StandardKey.Redo)
_HISTORY_ACTIONS = {"edit-undo", "edit-redo"}  # object names Qt gives these actions of the standard context menu


def one_line(text: str) -> str:
    """The text with each run of line breaks or tabs as one space: the detection reads the screen as lines of
    words joined by spaces."""
    return _NOT_SPACE.sub(" ", text)


class _OneLine(QValidator):
    """Turns what is typed, pasted or set into one line, keeping the cursor after the same characters."""

    def validate(self, text: str, position: int) -> tuple[QValidator.State, str, int]:
        return QValidator.State.Acceptable, one_line(text), len(one_line(text[:position]))


class _Input(QLineEdit):
    """Line edit without its own undo history: Undo and Redo reach the window, whose shortcuts undo the store."""

    focus_lost = Signal()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ShortcutOverride and isinstance(event, QKeyEvent) and _is_history(event):
            event.ignore()  # not taken by the line edit: the shortcut of the window runs
            return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if _is_history(event):
            event.ignore()  # without a shortcut of the window, nothing is undone rather than the line edit alone
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        super().focusOutEvent(event)
        if event.reason() is not Qt.FocusReason.PopupFocusReason:  # a context menu does not end the edit
            self.focus_lost.emit()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = self.context_menu()
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        menu.popup(event.globalPos())

    def context_menu(self) -> QMenu:
        """Standard context menu, without Undo and Redo."""
        menu = self.createStandardContextMenu()
        for action in menu.actions():
            if action.objectName() in _HISTORY_ACTIONS:
                menu.removeAction(action)
        while menu.actions() and menu.actions()[0].isSeparator():
            menu.removeAction(menu.actions()[0])
        return menu


class TextFindField(QWidget):
    """Label, large one-line field and error of the text to find; emits only on user edits, never on set_text.

    Line breaks and tabs, typed or pasted, become spaces. The field keeps no undo history of its own: Undo and Redo
    go to the window. It is never wider than METRICS.text_find_width, and narrows with the room it is given.
    """

    edited = Signal(str)
    """The user changed the text."""

    edit_finished = Signal()
    """The edit ends: Enter, or the focus leaves the field, except for its context menu."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMaximumWidth(METRICS.text_find_width)
        self.input = _Input()
        self.input.setProperty("textFind", True)
        self.input.setFixedHeight(METRICS.text_find_height)
        self.input.setValidator(_OneLine(self.input))
        label = QLabel(LABEL)
        label.setProperty("fieldLabel", True)
        label.setBuddy(self.input)
        self._error = QWidget()
        self._message = CenteredLabel()
        self._message.setProperty("message", "error")
        row = QHBoxLayout(self._error)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(METRICS.space(1))
        row.addWidget(IconLabel(Icon.CIRCLE_ALERT, theme, "error"))
        row.addWidget(self._message, 1)
        self._error.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(label)
        layout.addWidget(self.input)
        layout.addWidget(self._error)

        self.input.textEdited.connect(self.edited)
        self.input.returnPressed.connect(self.edit_finished)
        self.input.focus_lost.connect(self.edit_finished)

    def sizeHint(self) -> QSize:
        return QSize(METRICS.text_find_width, super().sizeHint().height())

    def text(self) -> str:
        return self.input.text()

    def set_text(self, text: str) -> None:
        """Shows the text, on one line; leaves the field, and its cursor, alone when it already shows it."""
        if one_line(text) != self.input.text():
            self.input.setText(text)

    def set_error(self, message: str | None) -> None:
        """Red border and message under the field, or neither."""
        set_style_property(self.input, "invalid", message is not None)
        self._message.setText(message or "")
        self._error.setVisible(message is not None)

    def focus_text(self) -> None:
        """Gives the focus to the field, its text selected, ready to be typed over."""
        self.input.setFocus(Qt.FocusReason.OtherFocusReason)
        self.input.selectAll()


def _is_history(event: QKeyEvent) -> bool:
    return any(event.matches(keys) for keys in _HISTORY)
