"""Row of the inspector for one property: label, editor, origin of the value, reset and message."""

import shiboken6
from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QWidget

from guimauve.gui.element_editor_next.components.badge import Dot
from guimauve.gui.element_editor_next.components.buttons import IconButton
from guimauve.gui.element_editor_next.components.editors import FieldEditor, describe, label_of
from guimauve.gui.element_editor_next.components.field_state import FieldState
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.components.text_fit import fit_text
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

    edit_finished = Signal()
    """The continuous edit ends; the panel closes its gesture."""

    def __init__(
        self, descriptor: FieldDescriptor, editor: FieldEditor, theme: ThemeManager, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.descriptor = descriptor
        self.editor = editor
        editor.edited.connect(self.edited)
        editor.edit_started.connect(self.edit_started)
        editor.edit_finished.connect(self.edit_finished)

        self._dot = Dot(theme)
        self._label = QLabel(descriptor.label)
        self._label.setProperty("sectionTitle" if descriptor.toggle else "fieldLabel", True)
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

        self._column = not descriptor.toggle and not descriptor.wide
        """The label sits in the column of the labels, sized with the field by resizeEvent."""
        label = self._label_box = QWidget()
        self._label_width = METRICS.label_width
        """Width of the column, kept here: a widget not shown yet may not report its fixed width."""
        if self._column:
            label.setFixedWidth(self._label_width)
        label.setMinimumHeight(METRICS.control_height)  # on the first line of a taller editor, e.g. with a button below
        row = QHBoxLayout(label)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(METRICS.space(1))
        self._row = row
        row.addWidget(self._dot)
        row.addWidget(self._label, 1)
        row.addWidget(self._code)
        row.addWidget(self._trial)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(METRICS.space(2))
        grid.setVerticalSpacing(METRICS.space(1))
        grid.setColumnStretch(1, 1)
        if descriptor.wide:  # label and reset on the first line, the editor under them
            grid.addWidget(label, 0, 0, 1, 2)
            grid.addWidget(self._reset, 0, 2)
            grid.addWidget(editor, 1, 0, 1, 2)
            grid.addWidget(self._message, 2, 0, 1, 3)
        else:
            grid.addWidget(label, 0, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(editor, 0, 1)
            grid.addWidget(self._reset, 0, 2, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(self._message, 1, 1, 1, 2)

        self._code_text = ""
        self._hint = ""
        self.set_state(FieldState(None))

    def set_state(self, state: FieldState) -> None:
        """Shows the state, without emitting anything."""
        self.editor.set_value(state.value, state.own, state.inherited)
        self.editor.set_invalid(state.error is not None)

        self._dot.setVisible(state.own)
        self._reset.setVisible(state.own)
        self._reset.setToolTip(_reset_hint(state))
        self._code_text = "" if state.code is None else f"{{{label_of(state.code)}}}"
        self._code.setToolTip("" if state.code is None else f"{HINTS[Source.CODE]}: {describe(state.code)}")
        self._code.setVisible(state.code is not None)

        self._trial.setVisible(state.trial)
        self._hint = "" if state.own or state.source is None else HINTS.get(state.source, "")
        self._fit_label()

        self._show_message(state)
        self.setEnabled(state.disabled_reason is None)
        self.setToolTip(state.disabled_reason or "")

    def column_room(self, width: int) -> int:
        """Widest column of labels that leaves room for the editor, in a field of this width."""
        if not self._column:
            return width
        grid = self.layout()
        assert isinstance(grid, QGridLayout)
        spacing = 2 * grid.horizontalSpacing()
        return width - _minimum_width(self.editor) - self._reset.sizeHint().width() - spacing

    def set_label_width(self, width: int) -> None:
        """Width of the column of labels, the same in every field of a tab so the editors stay aligned."""
        if self._column and width != self._label_width:
            self._label_width = width
            self._label_box.setFixedWidth(width)
            self._fit_label()

    def _fit_label(self) -> None:
        """Label and code value in the room left: the code keeps up to half of it, the label wraps or elides."""
        label, code = self.descriptor.label, self._code_text
        if not self._column:
            self._label.setText(label)
            self._code.setText(code)
            self._label.setToolTip(self._hint)
            return
        spacing = self._row.spacing()
        room = self._label_width - METRICS.dot - spacing
        if self._trial.isVisibleTo(self):
            room -= self._trial.sizeHint().width() + spacing
        code_room = 0
        if code:
            wanted = self._code.fontMetrics().horizontalAdvance(code)
            label_wanted = self._label.fontMetrics().horizontalAdvance(label)
            code_room = min(wanted, max(room - spacing - label_wanted, room // 2))
            room -= code_room + spacing
        self._code.setText(fit_text(code, self._code.fontMetrics(), code_room, lines=1))
        shown = fit_text(label, self._label.fontMetrics(), room)
        self._label.setText(shown)
        cut = shown.replace("\n", " ") != label
        self._label.setToolTip("\n".join(text for text in (label if cut else "", self._hint) if text))

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


class FormRow(QWidget):
    """Label in the column of the labels, then a widget, aligned with the property fields above or below."""

    def __init__(self, label: str, widget: QWidget, parent: QWidget | None = None):
        super().__init__(parent)
        self._widget = widget
        self._label = QLabel(label)
        self._label.setProperty("fieldLabel", True)
        self._label.setFixedWidth(METRICS.label_width)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(self._label)
        layout.addWidget(widget, 1)

    def column_room(self, width: int) -> int:
        return width - _minimum_width(self._widget) - METRICS.space(2)

    def set_label_width(self, width: int) -> None:
        self._label.setFixedWidth(width)


class LabelColumn(QObject):
    """One width for the column of labels of the rows of a scroll area, kept as they are shown and resized.

    The column takes a share of the room of the rows (METRICS.label_ratio), never less than METRICS.label_width,
    and never so much that an editor no longer fits beside it. The room is read from the viewport, which rows
    wider than their editors allow cannot widen.

    :param viewport: Viewport of the scroll area showing the rows, centered in it.
    """

    def __init__(self, viewport: QWidget, parent: QObject | None = None):
        super().__init__(parent)
        self._viewport = viewport
        self._rows: list[PropertyField | FormRow] = []
        self._applying = False
        viewport.installEventFilter(self)

    def add(self, row: "PropertyField | FormRow") -> None:
        self._rows.append(row)
        row.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.apply()
        return False

    def apply(self) -> None:
        if self._applying:
            return
        self._rows = [row for row in self._rows if shiboken6.isValid(row)]  # rows of a variant are replaced
        shown = [row for row in self._rows if row.isVisible()]
        if not shown:
            return
        room = max(self._room(row) for row in shown)
        column = min(round(room * METRICS.label_ratio), min(row.column_room(room) for row in shown))
        self._applying = True
        try:
            for row in self._rows:
                row.set_label_width(max(METRICS.label_width, column))
        finally:
            self._applying = False

    def _room(self, row: QWidget) -> int:
        """Width the row has in the viewport, between margins as wide on both sides."""
        return self._viewport.width() - 2 * row.mapTo(self._viewport, QPoint(0, 0)).x()


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


def _minimum_width(widget: QWidget) -> int:
    """Narrowest width the layout gives the widget: its own minimum or the one its content needs."""
    return widget.minimumSizeHint().expandedTo(widget.minimumSize()).width()
