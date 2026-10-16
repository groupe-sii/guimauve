"""Choice between a few values, shown as pills on a track."""

from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QWidget


class SegmentedControl(QFrame):
    """One value among a few, such as Default / On / Off.

    The control takes the focus as a whole: Tab reaches it once, then Left and Right change the value.

    :param options: Value and label of each segment, in display order; the first one is selected.
    """

    activated = Signal(object)
    """The user selected another value, which is given; never emitted by set_value."""

    def __init__(self, options: Sequence[tuple[Any, str]], parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("segmented", True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._values = [value for value, _ in options]
        self._index = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(2)
        self._group = QButtonGroup(self)
        for index, (_, label) in enumerate(options):
            button = QPushButton(label, self)
            button.setProperty("segment", True)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._group.addButton(button, index)
            layout.addWidget(button)
        self._group.idClicked.connect(self._select)
        self._check(0)

    def value(self) -> Any:
        return self._values[self._index]

    def set_value(self, value: Any) -> None:
        """Selects a value without emitting activated."""
        self._check(self._values.index(value))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        steps = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}
        if event.key() not in steps:
            super().keyPressEvent(event)
            return
        index = self._index + steps[Qt.Key(event.key())]
        if 0 <= index < len(self._values):
            self._check(index)
            self.activated.emit(self._values[index])

    def _check(self, index: int) -> None:
        self._index = index
        self._group.button(index).setChecked(True)

    def _select(self, index: int) -> None:
        """Clicked segment, already checked by the group."""
        if index != self._index:
            self._index = index
            self.activated.emit(self._values[index])
