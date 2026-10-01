"""Colored ticks over the timeline, one per key/click/scroll event."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from guimauve.gui.replay_editor.constants import EVENT_COLORS, HIDDEN_EVENT_ACTIONS
from guimauve.models.input_event import InputEvent


class EventTrack(QWidget):
    """Draws colored ticks and lets the user click one to jump the playhead.

    :cvar event_clicked: Emitted with a time (in seconds from the start
        of the recording) when the user clicks close enough to a tick.
    """

    event_clicked = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        :param parent: Optional Qt parent widget.
        """
        super().__init__(parent)
        self.setFixedHeight(14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._events: list[InputEvent] = []
        self._first_t: float = 0.0
        self._duration: float = 0.0

    def set_events(self, events: list[InputEvent]) -> None:
        """Load a new event list and recompute the tick positions.

        :param events: The events to draw. An empty list clears the
            track and disables click detection.
        """
        self._events = list(events) if events else []
        if self._events:
            self._first_t = self._events[0].t
            self._duration = max(0.001, self._events[-1].t - self._first_t)
        else:
            self._first_t = 0.0
            self._duration = 0.0
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint one colored tick per non-hidden event.

        :param event: The Qt paint event.
        """
        if not self._events or self._duration <= 0:
            return
        painter = QPainter(self)
        w = self.width()
        h = self.height()
        for ev in self._events:
            if ev.action in HIDDEN_EVENT_ACTIONS:
                continue
            color = EVENT_COLORS.get(ev.action)
            if color is None:
                continue
            rel_t = ev.t - self._first_t
            x = int(rel_t / self._duration * (w - 2))
            painter.fillRect(x, 0, 2, h, color)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Find the nearest tick to the click and emit :data:`event_clicked`.

        :param event: The Qt mouse event.
        """
        if not self._events or self._duration <= 0:
            return
        w = self.width()
        click_x = event.pos().x()
        tolerance = 6

        best_ev: InputEvent | None = None
        best_dist = tolerance + 1
        for ev in self._events:
            if ev.action in HIDDEN_EVENT_ACTIONS or ev.action not in EVENT_COLORS:
                continue
            rel_t = ev.t - self._first_t
            x = int(rel_t / self._duration * (w - 2))
            d = abs(x - click_x)
            if d < best_dist:
                best_ev = ev
                best_dist = d

        if best_ev is not None:
            self.event_clicked.emit(best_ev.t - self._first_t)
