"""Editor of one axis of the fixed position."""

from typing import Any

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from guimauve.gui.common.fields import bounds
from guimauve.gui.element_editor_next.components.axis import NOT_SET, AxisMode, AxisPosition
from guimauve.gui.element_editor_next.components.editors import FieldEditor, NumberEditor
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.components.segmented import SegmentedControl
from guimauve.gui.element_editor_next.schema import FieldDescriptor
from guimauve.gui.element_editor_next.theme import METRICS
from guimauve.models.element import Element

_SUFFIXES = {AxisMode.ABSOLUTE: "px on screen", AxisMode.FROM_MOUSE: "px from mouse"}


class AxisEditor(FieldEditor):
    """Not set, Absolute or From mouse, then the number of pixels; edits an AxisPosition.

    Each mode has its own number box. A position on a screen is never negative, except from the primary screen
    (screen 0); a distance from the mouse can be. A negative value already set stays shown, with its error.
    """

    def __init__(self, descriptor: FieldDescriptor, parent: QWidget | None = None):
        super().__init__(parent)
        assert descriptor.relative is not None  # an axis of the fixed position
        self._position = NOT_SET
        self._negative_allowed = False
        self._absolute_bounds = descriptor.bounds

        self._modes = SegmentedControl(
            [(AxisMode.NOT_SET, "Not set"), (AxisMode.ABSOLUTE, "Absolute"), (AxisMode.FROM_MOUSE, "From mouse")]
        )
        self._modes.activated.connect(self._mode_chosen)
        self._amounts = {
            AxisMode.ABSOLUTE: NumberEditor(descriptor.bounds, is_float=False),
            AxisMode.FROM_MOUSE: NumberEditor(bounds(Element, descriptor.relative), is_float=False),
        }
        self._suffix = QLabel()
        self._suffix.setProperty("muted", True)

        amount = QHBoxLayout()
        amount.setContentsMargins(0, 0, 0, 0)
        amount.setSpacing(METRICS.space(2))
        for mode, editor in self._amounts.items():
            editor.setFixedWidth(METRICS.number_width)
            editor.edited.connect(lambda value, mode=mode: self.edited.emit(AxisPosition(mode, value)))
            amount.addWidget(editor)
        amount.addWidget(self._suffix, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space(1))
        layout.addWidget(self._modes)
        layout.addLayout(amount)
        self._bound_absolute()
        self._show_mode(AxisMode.NOT_SET)

    def set_negative_allowed(self, allowed: bool) -> None:
        """Whether an absolute position can be negative: only from the primary screen, i.e. with screen 0."""
        self._negative_allowed = allowed
        self._bound_absolute()

    def set_value(self, value: Any, own: bool, inherited: Any) -> None:
        self._position = value if isinstance(value, AxisPosition) else NOT_SET
        self._bound_absolute()
        self._modes.set_value(self._position.mode)
        self._modes.set_reselectable(not own)
        set_style_property(self._modes, "inherited", not own)
        for mode, editor in self._amounts.items():
            editor.set_value(self._position.amount if mode is self._position.mode else 0, own, None)
        self._show_mode(self._position.mode)

    def set_invalid(self, invalid: bool) -> None:
        for editor in self._amounts.values():
            editor.set_invalid(invalid)

    def _bound_absolute(self) -> None:
        low, high = self._absolute_bounds
        if not self._negative_allowed:  # widened to show a negative value already set
            shown = self._position.amount if self._position.mode is AxisMode.ABSOLUTE else 0
            low = min(0 if low is None else low, shown)
        self._amounts[AxisMode.ABSOLUTE].set_bounds((low, high))

    def _mode_chosen(self, mode: AxisMode) -> None:
        """Another mode starts at 0; the inherited mode chosen again keeps its amount."""
        amount = self._position.amount if mode is self._position.mode else 0
        self._show_mode(mode)
        self.edited.emit(NOT_SET if mode is AxisMode.NOT_SET else AxisPosition(mode, amount))

    def _show_mode(self, mode: AxisMode) -> None:
        for each, editor in self._amounts.items():
            editor.setVisible(each is mode)
        self._suffix.setText(_SUFFIXES.get(mode, ""))
        self._suffix.setVisible(mode is not AxisMode.NOT_SET)
