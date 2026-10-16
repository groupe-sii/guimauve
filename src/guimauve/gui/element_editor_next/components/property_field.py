"""Row of the inspector for one property: label, editor, origin of the value, reset and message."""

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QWidget

from guimauve.gui.element_editor_next.components.badge import Dot
from guimauve.gui.element_editor_next.components.buttons import IconButton
from guimauve.gui.element_editor_next.components.editors import FieldEditor, label_of
from guimauve.gui.element_editor_next.components.field_state import FieldState
from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.schema import FieldDescriptor
from guimauve.gui.element_editor_next.state import Source
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

TAGS = {
    Source.DEFAULT: "default",
    Source.ELEMENT: "element",
    Source.CODE: "in code",
    Source.ELEMENT_TRIAL: "element trial",
}
"""Tag of an inherited value, by its layer."""

HINTS = {
    Source.DEFAULT: "Default value, from the configuration file",
    Source.ELEMENT: "Value of the element",
    Source.CODE: "Value set in the code for this call",
    Source.ELEMENT_TRIAL: "Value tried on the element, not saved",
}


class PropertyField(QWidget):
    """Shows a FieldState and forwards the user edits; it never talks to the store.

    :param editor: Generic editor from editor_for, or the editor of a special field.
    """

    edited = Signal(object)
    """The user set a value at the level of the tab."""

    reset_requested = Signal()
    """The user asked for the inherited value: reset button, or Default on a boolean."""

    edit_started = Signal()
    """A continuous edit starts; the panel opens a gesture for the next edited values."""

    def __init__(
        self, descriptor: FieldDescriptor, editor: FieldEditor, theme: ThemeManager, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.descriptor = descriptor
        self.editor = editor
        editor.edited.connect(self._edited)
        editor.edit_started.connect(self.edit_started)

        self._dot = Dot(theme)
        self._braces = IconLabel(Icon.BRACES, theme, "text_secondary")
        self._braces.setToolTip(HINTS[Source.CODE])
        self._label = QLabel(descriptor.label)
        self._label.setProperty("sectionTitle" if descriptor.toggle else "fieldLabel", True)
        self._tag = QLabel()
        self._tag.setProperty("tag", True)
        self._reset = IconButton(Icon.ROTATE_CCW, theme, "Reset to inherited value")
        self._reset.setObjectName("reset")
        self._reset.clicked.connect(self.reset_requested)
        self._message = QLabel()
        self._message.setWordWrap(True)
        for widget in (self._dot, self._braces, self._reset):
            _keep_place(widget)

        label = QHBoxLayout()
        label.setSpacing(METRICS.space(1))
        label.addWidget(self._dot)
        label.addWidget(self._label)
        label.addWidget(self._braces)
        label.addStretch()

        value = QHBoxLayout()
        value.setSpacing(METRICS.space(2))
        value.addWidget(editor, 1)
        value.addWidget(self._tag)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(METRICS.space(2))
        grid.setVerticalSpacing(METRICS.space(1))
        grid.setColumnMinimumWidth(0, METRICS.label_width)
        grid.setColumnStretch(1, 1)
        grid.addLayout(label, 0, 0)
        grid.addLayout(value, 0, 1)
        grid.addWidget(self._reset, 0, 2)
        grid.addWidget(self._message, 1, 1, 1, 2)

        self.set_state(FieldState(None))

    def set_state(self, state: FieldState) -> None:
        """Shows the state, without emitting anything."""
        self.editor.set_value(state.value, state.own, state.inherited)
        self.editor.set_invalid(state.error is not None)

        self._dot.setVisible(state.own)
        self._reset.setVisible(state.own)
        self._reset.setToolTip(f"Reset to {label_of(state.inherited)}" if state.inherited is not None else "Reset")
        self._braces.setVisible(state.code is not None or state.source is Source.CODE)

        tag = "trial" if state.trial else TAGS.get(state.source, "") if state.source else ""
        self._tag.setText(tag)
        self._tag.setVisible(bool(tag))
        self._label.setToolTip(HINTS.get(state.source, "") if state.source else "")

        self._show_message(state)
        self.setEnabled(state.disabled_reason is None)
        self.setToolTip(state.disabled_reason or "")

    def _show_message(self, state: FieldState) -> None:
        if state.error:
            kind, text = "error", state.error
        elif state.warning:
            kind, text = "warning", state.warning
        elif state.code is not None:
            kind, text = "note", f"{label_of(state.code)} in code for this call"
        else:
            kind, text = "", ""
        set_style_property(self._message, "message", kind)
        self._message.setText(text)
        self._message.setVisible(bool(text))

    def _edited(self, value: Any) -> None:
        if value is None:
            self.reset_requested.emit()
        else:
            self.edited.emit(value)


def _keep_place(widget: QWidget) -> None:
    """Keeps the place of the widget while hidden, so the rows stay aligned."""
    policy = widget.sizePolicy()
    policy.setRetainSizeWhenHidden(True)
    widget.setSizePolicy(policy)
