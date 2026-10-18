"""Editors of the generic property types, chosen from the pydantic annotation of the field."""

import types
from enum import Enum
from typing import Any, Union, get_args, get_origin

from PySide6.QtCore import QLocale, Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QSlider, QSpinBox, QWidget

from guimauve.enums import MatchSort, MouseDirection, OcrFidelity
from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.components.segmented import SegmentedControl
from guimauve.gui.element_editor_next.components.switch import Switch
from guimauve.gui.element_editor_next.schema import FIXED_POSITION_KEYS, FieldDescriptor
from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager
from guimauve.models.area import Area
from guimauve.models.element import Element

_UNBOUNDED = 1_000_000
_SLIDER_STEPS = 100

ENUM_LABELS: dict[Enum, str] = {
    MouseDirection.STRAIGHT: "Straight",
    MouseDirection.XY_X: "X then Y",
    MouseDirection.XY_Y: "Y then X",
    MatchSort.CONFIDENCE: "Confidence",
    MatchSort.XY_POSITION: "Position",
    OcrFidelity.FAST: "Fast",
    OcrFidelity.BALANCED: "Balanced",
    OcrFidelity.ACCURATE: "Accurate",
}


def label_of(value: Any) -> str:
    """Value as shown to the user, short enough for a label, e.g. "on", "0.85", "X then Y" or "custom"."""
    if isinstance(value, Area):
        return "custom"  # as the Custom… choice of the search area; describe gives the coordinates
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, Enum):
        return ENUM_LABELS.get(value, value.name.replace("_", " ").capitalize())
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, list | tuple):
        return ", ".join(label_of(item) for item in value)
    return str(value)


def describe(value: Any) -> str:
    """Value in full, for a tooltip, e.g. "x 120, y 80, 640 × 360" for an area."""
    if isinstance(value, Area):
        x, y, width, height = value.as_xywh()
        return f"x {x}, y {y}, {width} × {height}"
    return label_of(value)


class FieldEditor(QWidget):
    """Edits one value; emits only on user actions, never on set_value."""

    edited = Signal(object)
    """The user chose a value."""

    edit_started = Signal()
    """A continuous edit starts, such as dragging a slider: the next edited values form one gesture."""

    def set_value(self, value: Any, own: bool, inherited: Any) -> None:
        """Shows the value; muted when it is inherited (not own). inherited is what applies without it."""
        raise NotImplementedError

    def set_invalid(self, invalid: bool) -> None:
        """Red border on the input, when the value has an error."""


class SwitchEditor(FieldEditor):
    """Switch of a detection method; the reset button goes back to the inherited value."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._switch = Switch(theme)
        self._switch.clicked.connect(lambda checked: self.edited.emit(checked))
        _single(self, self._switch, Qt.AlignmentFlag.AlignRight)

    def set_value(self, value: Any, own: bool, inherited: Any) -> None:
        self._switch.setChecked(bool(value))


class ChoiceEditor(FieldEditor):
    """One value among a few, as segments; an inherited value is shown muted and can be clicked to set it."""

    def __init__(self, options: list[tuple[Any, str]], parent: QWidget | None = None):
        super().__init__(parent)
        self._control = SegmentedControl(options)
        self._control.activated.connect(self.edited)
        _single(self, self._control)

    def set_value(self, value: Any, own: bool, inherited: Any) -> None:
        if value is not None:
            self._control.set_value(value)
        self._control.set_reselectable(not own)
        set_style_property(self._control, "inherited", not own)


class BoolEditor(ChoiceEditor):
    def __init__(self, parent: QWidget | None = None):
        super().__init__([(True, "On"), (False, "Off")], parent)


class EnumEditor(ChoiceEditor):
    def __init__(self, enum: type[Enum], parent: QWidget | None = None):
        super().__init__([(member, label_of(member)) for member in enum], parent)


class NumberEditor(FieldEditor):
    """Number box bounded by pydantic, with a slider for the thresholds from 0 to 1.

    A typed value is sent on Enter or when the box loses the focus, not at every key.
    """

    def __init__(self, bounds: tuple[Any, Any], is_float: bool, parent: QWidget | None = None):
        super().__init__(parent)
        low = -_UNBOUNDED if bounds[0] is None else bounds[0]
        high = _UNBOUNDED if bounds[1] is None else bounds[1]
        self._box: QSpinBox | QDoubleSpinBox = _DoubleSpinBox() if is_float else _SpinBox()
        if isinstance(self._box, QDoubleSpinBox):
            self._box.setDecimals(2)
            self._box.setSingleStep(0.01 if high <= 1 else 0.1)
        self._box.setRange(low, high)
        self._box.setLocale(QLocale.c())  # a dot as decimal separator, as in the YAML files
        self._box.setKeyboardTracking(False)
        self._box.valueChanged.connect(lambda value: self.edited.emit(value))

        self._box.lineEdit().setTextMargins(METRICS.space(2), 0, METRICS.space(2), 0)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space(2))

        self._slider: QSlider | None = None
        if is_float and (low, high) == (0, 1):
            self._slider = _Slider(Qt.Orientation.Horizontal)
            self._slider.setRange(0, _SLIDER_STEPS)
            self._slider.sliderPressed.connect(self.edit_started)
            self._slider.valueChanged.connect(self._slid)
            self._box.setFixedWidth(METRICS.number_width)
            layout.addWidget(self._slider, 1)
        layout.addWidget(self._box, 0 if self._slider else 1)

    def set_value(self, value: Any, own: bool, inherited: Any) -> None:
        for widget in (self._box, self._slider):
            if widget is not None:
                widget.blockSignals(True)
        if value is None:
            self._box.clear()
        else:
            self._box.setValue(value)
            if self._slider is not None:
                self._slider.setValue(round(value * _SLIDER_STEPS))
        for widget in (self._box, self._slider):
            if widget is not None:
                widget.blockSignals(False)
        set_style_property(self._box, "inherited", not own)

    def set_invalid(self, invalid: bool) -> None:
        set_style_property(self._box, "invalid", invalid)

    def _slid(self, position: int) -> None:
        assert isinstance(self._box, QDoubleSpinBox)  # only thresholds have a slider
        value = position / _SLIDER_STEPS
        self._box.blockSignals(True)
        self._box.setValue(value)
        self._box.blockSignals(False)
        self.edited.emit(value)


class _SpinBox(QSpinBox):
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()  # the wheel scrolls the inspector, never changes a value


class _DoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class _Slider(QSlider):
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


def editor_for(descriptor: FieldDescriptor, theme: ThemeManager) -> FieldEditor | None:
    """Generic editor of the field, or None for a field with its own editor (target, screen, search area,
    fixed position)."""
    if descriptor.key in FIXED_POSITION_KEYS:
        return None
    if descriptor.toggle:
        return SwitchEditor(theme)

    types_ = _types(Element.model_fields[descriptor.key].annotation)
    if types_ == {bool}:
        return BoolEditor()
    enums = [kind for kind in types_ if isinstance(kind, type) and issubclass(kind, Enum)]
    if len(types_) == 1 and enums:
        return EnumEditor(enums[0])
    if types_ and types_ <= {int, float}:
        return NumberEditor(descriptor.bounds, is_float=float in types_)
    return None


def _types(annotation: Any) -> set[type]:
    """Types of an annotation without None, e.g. {int, float} for int | float | None."""
    if get_origin(annotation) in (Union, types.UnionType):
        return {arg for arg in get_args(annotation) if arg is not type(None)}
    return {annotation}


def _single(editor: QWidget, widget: QWidget, alignment: Qt.AlignmentFlag | None = None) -> None:
    layout = QHBoxLayout(editor)
    layout.setContentsMargins(0, 0, 0, 0)
    if alignment is None:
        layout.addWidget(widget)
    else:
        layout.addWidget(widget, 0, alignment)
