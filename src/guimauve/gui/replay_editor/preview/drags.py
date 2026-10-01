"""Trails drawn while a mouse button is held and moving."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsScene

from guimauve.gui.replay_editor.constants import BUTTON_COLORS
from guimauve.gui.replay_editor.preview.compute import Drag

_TRAIL_WINDOW: float = 1.0

_TRAIL_WIDTH: float = 6.0
_DASH_PATTERN: list[float] = [3.0, 3.0]


class DragRenderer:
    """Renders drag trails as thick dashed lines with a rolling fade.

    Each drag is drawn as a series of short segments covering the last
    :data:`_TRAIL_WINDOW` seconds of the drag. Older points naturally
    disappear from view as time moves on, which also handles the fade
    after ``mouse_up`` (no more points feed in, and the tail catches
    up within one second).
    """

    def __init__(self, scene: QGraphicsScene) -> None:
        """
        :param scene: The scene drag trails are added to.
        """
        self._scene = scene
        self._items: list[QGraphicsPathItem] = []
        self._drags: list[Drag] = []

    def set_drags(self, drags: list[Drag]) -> None:
        """Configure the source drags for future :meth:`render` calls.

        :param drags: Pre-computed drags from
            :func:`preview.compute.compute_drags`.
        """
        self._drags = drags

    def render(self, current_t: float) -> None:
        """Clear previous trails and draw the ones visible at ``current_t``.

        :param current_t: Current relative time, in seconds.
        """
        self._clear()
        window_start = current_t - _TRAIL_WINDOW
        for drag in self._drags:
            if current_t < drag["start_t"]:
                continue
            end_or_now = drag["end_t"] if drag["end_t"] is not None else current_t
            if current_t > end_or_now + _TRAIL_WINDOW:
                continue

            visible = [(t, x, y) for (t, x, y) in drag["points"] if window_start <= t <= current_t]
            if len(visible) < 2:
                continue

            base_color = BUTTON_COLORS.get(drag["button"], QColor("gray"))
            self._draw_trail(visible, base_color, current_t)

    def clear(self) -> None:
        """Remove all drag-trail items from the scene."""
        self._clear()

    def _draw_trail(
        self,
        visible: list[tuple[float, int, int]],
        base_color: QColor,
        current_t: float,
    ) -> None:
        """Draw the trail as one dashed segment per point pair.

        The opacity of each segment is a linear function of how old
        it is: fresh (at ``current_t``) is fully opaque, and points
        aged :data:`_TRAIL_WINDOW` seconds fall to zero.

        :param visible: Points within the fade window,
            as ``(t, x, y)`` tuples in chronological order.
        :param base_color: The button color.
        :param current_t: Current relative time, in seconds.
        """
        for i in range(1, len(visible)):
            t_prev, x_prev, y_prev = visible[i - 1]
            t, x, y = visible[i]

            age = current_t - t
            alpha = max(0.0, 1.0 - age / _TRAIL_WINDOW)
            if alpha <= 0:
                continue

            color = QColor(base_color)
            color.setAlphaF(alpha)

            path = QPainterPath()
            path.moveTo(x_prev, y_prev)
            path.lineTo(x, y)

            item = QGraphicsPathItem(path)
            pen = QPen(color, _TRAIL_WIDTH)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setDashPattern(_DASH_PATTERN)
            item.setPen(pen)
            item.setBrush(QBrush(Qt.NoBrush))
            item.setZValue(998)
            self._scene.addItem(item)
            self._items.append(item)

    def _clear(self) -> None:
        """Remove all drag-trail items from the scene."""
        for item in self._items:
            self._scene.removeItem(item)
        self._items.clear()
