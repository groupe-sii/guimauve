"""Row of the inspector for one property: label, editor, origin of the value, reset and message."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QWidget

from guimauve.gui.element_editor_next.components.badge import Dot
from guimauve.gui.element_editor_next.components.buttons import IconButton
from guimauve.gui.element_editor_next.components.editors import FieldEditor, describe, label_of
from guimauve.gui.element_editor_next.components.field_state import FieldState
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.schema import FieldDescriptor
from guimauve.gui.element_editor_next.state import Source
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

LAYER_NAMES = {
    Source.DEFAULT: "default",
    Source.ELEMENT: "element",
    Source.ELEMENT_TRIAL: "element trial",
}
"""Short name of a layer, in the tooltip of the reset button."""

HINTS = {
    Source.DEFAULT: "Default value, from the configuration file",
    Source.ELEMENT: "Value of the element",
    Source.CODE: "Value set in the code for this call",
    Source.ELEMENT_TRIAL: "Value tried on the element, not saved",
}


class PropertyField(QWidget):
    """Shows a FieldState and forwards the user edits; it never talks to the store.

    An inherited value has no dot and is shown muted, in a recessed input; the tooltip of the label tells where it
    comes from. A value from the code is shown beside the label, between braces.

    :param editor: Generic editor from editor_for, or the editor of a special field.
    """

    edited = Signal(object)
    """The user set a value at the level of the tab."""

    reset_requested = Signal()
    """The user asked for the inherited value."""

    edit_started = Signal()
    """A continuous edit starts; the panel opens a gesture for the next edited values."""

    def __init__(
        self, descriptor: FieldDescriptor, editor: FieldEditor, theme: ThemeManager, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.descriptor = descriptor
        self.editor = editor
        editor.edited.connect(self.edited)
        editor.edit_started.connect(self.edit_started)

        self._dot = Dot(theme)
        self._label = QLabel(descriptor.label)
        self._label.setProperty("sectionTitle" if descriptor.toggle else "fieldLabel", True)
        self._label.setWordWrap(not descriptor.toggle)
        self._code = QLabel()
        self._code.setProperty("codeValue", True)
        self._trial = QLabel("trial")
        self._trial.setProperty("tag", True)
        self._reset = IconButton(Icon.ROTATE_CCW, theme, "Reset to inherited value")
        self._reset.setObjectName("reset")
        self._reset.clicked.connect(self.reset_requested)
        self._message = QLabel()
        self._message.setObjectName("message")
        self._message.setWordWrap(True)
        for widget in (self._dot, self._reset):
            _keep_place(widget)

        label = QWidget()
        if not descriptor.toggle:  # a fixed column keeps the editors aligned from row to row
            label.setFixedWidth(METRICS.label_width)
        row = QHBoxLayout(label)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(METRICS.space(1))
        row.addWidget(self._dot)
        row.addWidget(self._label, 1)
        row.addWidget(self._code)
        row.addWidget(self._trial)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(METRICS.space(2))
        grid.setVerticalSpacing(METRICS.space(1))
        grid.setColumnStretch(1, 1)
        grid.addWidget(label, 0, 0)
        grid.addWidget(editor, 0, 1)
        grid.addWidget(self._reset, 0, 2)
        grid.addWidget(self._message, 1, 1, 1, 2)

        self.set_state(FieldState(None))

    def set_state(self, state: FieldState) -> None:
        """Shows the state, without emitting anything."""
        self.editor.set_value(state.value, state.own, state.inherited)
        self.editor.set_invalid(state.error is not None)

        self._dot.setVisible(state.own)
        self._reset.setVisible(state.own)
        self._reset.setToolTip(_reset_hint(state))
        self._code.setText("" if state.code is None else f"{{{label_of(state.code)}}}")
        self._code.setToolTip("" if state.code is None else f"{HINTS[Source.CODE]}: {describe(state.code)}")
        self._code.setVisible(state.code is not None)

        self._trial.setVisible(state.trial)
        self._label.setToolTip("" if state.own or state.source is None else HINTS.get(state.source, ""))

        self._show_message(state)
        self.setEnabled(state.disabled_reason is None)
        self.setToolTip(state.disabled_reason or "")

    def _show_message(self, state: FieldState) -> None:
        if state.error:
            kind, text = "error", state.error
        elif state.warning:
            kind, text = "warning", state.warning
        else:
            kind, text = "", ""
        set_style_property(self._message, "message", kind)
        self._message.setText(text)
        self._message.setVisible(bool(text))


def _reset_hint(state: FieldState) -> str:
    """Where the reset leads, e.g. "Reset to on (element)"."""
    if state.inherited is None or state.source is None:
        return "Reset"
    return f"Reset to {label_of(state.inherited)} ({LAYER_NAMES.get(state.source, '')})"


def _keep_place(widget: QWidget) -> None:
    """Keeps the place of the widget while hidden, so the rows stay aligned."""
    policy = widget.sizePolicy()
    policy.setRetainSizeWhenHidden(True)
    widget.setSizePolicy(policy)
