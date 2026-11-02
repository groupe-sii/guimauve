"""Choice between a few values, shown as pills on a track."""

from collections.abc import Sequence
from typing import Any

from PySide6.QtCore import QDynamicPropertyChangeEvent, QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFocusEvent, QKeyEvent
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QWidget

from guimauve.gui.element_editor_next.components.restyle import set_style_property
from guimauve.gui.element_editor_next.theme import MOTION

KEYBOARD_REASONS = (
    Qt.FocusReason.TabFocusReason,
    Qt.FocusReason.BacktabFocusReason,
    Qt.FocusReason.ShortcutFocusReason,
)


class SegmentedControl(QFrame):
    """One value among a few, such as Default / On / Off.

    The value chosen sits on a pill, which slides to the value the user chooses; a value set by the program, or
    inherited, shows at once, an inherited one outlined without pill. The control takes the focus as a whole: Tab
    reaches it once, then Left and Right change the value. Its focus shows only when it came from the keyboard, not
    from a click; back to the window, it shows as it did.

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
        self._reselectable = False

        self.thumb = QFrame(self)  # first child, so under the segments
        self.thumb.setProperty("segmentThumb", True)
        self.thumb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._slide = QPropertyAnimation(self.thumb, b"geometry", self)
        self._slide.setDuration(MOTION.segment_slide)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide.finished.connect(lambda: self._place_thumb(animate=False))  # in case the layout moved meanwhile

        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(2)
        self._group = QButtonGroup(self)
        for index, (_, label) in enumerate(options):
            button = QPushButton(label, self)
            button.setProperty("segment", True)
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.installEventFilter(self)  # the pill follows the segment chosen when the layout moves it
            self._group.addButton(button, index)
            layout.addWidget(button)
        self._group.idClicked.connect(self._select)
        self._check(0)

    def value(self) -> Any:
        return self._values[self._index]

    def set_value(self, value: Any) -> None:
        """Selects a value without emitting activated; the value already chosen keeps its pill sliding."""
        index = self._values.index(value)
        if index == self._index and self._group.button(index).isChecked():
            return  # often the value just chosen, coming back from the store
        self._check(index)

    def set_accent(self, value: Any) -> None:
        """Fills the pill with the accent while this value is chosen, e.g. for the Test mode."""
        self.segment(value).setProperty("accentSegment", True)
        self._place_thumb(animate=False)

    def segment(self, value: Any) -> QPushButton:
        """Button of a value, e.g. to style it apart."""
        button = self._group.button(self._values.index(value))
        assert isinstance(button, QPushButton)
        return button

    def set_reselectable(self, reselectable: bool) -> None:
        """Whether a click on the selected segment emits activated too, e.g. to set an inherited value."""
        self._reselectable = reselectable

    def event(self, event: QEvent) -> bool:
        if isinstance(event, QDynamicPropertyChangeEvent) and event.propertyName().data() == b"inherited":
            self.thumb.setVisible(not self.property("inherited"))  # an inherited value is outlined instead
            if not self._sliding():
                self._place_thumb(animate=False)  # where the value is now, after being hidden
        return super().event(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        chosen = watched is self._group.button(self._index)
        if chosen and event.type() in (QEvent.Type.Move, QEvent.Type.Resize) and not self._sliding():
            self.thumb.setGeometry(self._group.button(self._index).geometry())
        return super().eventFilter(watched, event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        if event.reason() != Qt.FocusReason.ActiveWindowFocusReason:
            set_style_property(self, "keyboardFocus", event.reason() in KEYBOARD_REASONS)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        steps = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}
        if event.key() not in steps:
            super().keyPressEvent(event)
            return
        index = self._index + steps[Qt.Key(event.key())]
        if 0 <= index < len(self._values):
            self._check(index, animate=True)
            self.activated.emit(self._values[index])

    def _check(self, index: int, animate: bool = False) -> None:
        self._index = index
        self._group.button(index).setChecked(True)
        self._place_thumb(animate)

    def _select(self, index: int) -> None:
        """Clicked segment, already checked by the group."""
        if index != self._index or self._reselectable:
            self._index = index
            self._place_thumb(animate=True)
            self.activated.emit(self._values[index])

    def _place_thumb(self, animate: bool) -> None:
        """Puts the pill under the segment chosen, sliding there from where it is when animated and shown."""
        button = self._group.button(self._index)
        for other in self._group.buttons():  # a font cannot change with :checked, a property can
            set_style_property(other, "chosen", other is button)
        set_style_property(self.thumb, "accent", bool(button.property("accentSegment")))
        self._slide.stop()
        if animate and self.thumb.isVisible():
            self._slide.setStartValue(self.thumb.geometry())
            self._slide.setEndValue(button.geometry())
            self._slide.start()
        else:
            self.thumb.setGeometry(button.geometry())

    def _sliding(self) -> bool:
        return self._slide.state() == QPropertyAnimation.State.Running
