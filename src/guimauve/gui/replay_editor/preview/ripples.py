"""Expanding rings drawn at each mouse-down, in the button's color."""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene

from guimauve.gui.replay_editor.constants import (
    BUTTON_COLORS,
    RIPPLE_LIFETIME,
    RIPPLE_MAX_RADIUS,
    RIPPLE_MAX_RADIUS_DOUBLE,
)
from guimauve.models.input_event import InputEvent

PositionAtFn = Callable[[float], tuple[int, int] | None]


class RippleRenderer:
    """Draws short-lived expanding circles at every ``mouse_down``.

    A ripple grows to :data:`RIPPLE_MAX_RADIUS` (or
    :data:`RIPPLE_MAX_RADIUS_DOUBLE` for double clicks) over
    :data:`RIPPLE_LIFETIME` seconds while fading out.
    """

    def __init__(self, scene: QGraphicsScene, position_at: PositionAtFn) -> None:
        """
        :param scene: The scene ripples are added to.
        :param position_at: Function returning the cursor position at a
            given relative time, so ripples can be anchored to where
            the mouse actually was when it was clicked.
        """
        self._scene = scene
        self._position_at = position_at
        self._items: list[QGraphicsEllipseItem] = []
        self._events: list[InputEvent] = []
        self._first_t: float = 0.0
        self._double_clicks: set[int] = set()

    def set_events(
        self,
        events: list[InputEvent],
        first_t: float,
        double_clicks: set[int],
    ) -> None:
        """Configure the source events for future :meth:`render` calls.

        :param events: All recorded events, in order.
        :param first_t: Timestamp of the first event.
        :param double_clicks: Set of event indices flagged as double clicks.
        """
        self._events = events
        self._first_t = first_t
        self._double_clicks = double_clicks

    def render(self, current_t: float) -> None:
        """Clear previous ripples and draw the ones alive at ``current_t``.

        :param current_t: Current relative time, in seconds.
        """
        self._clear()
        window_start = current_t - RIPPLE_LIFETIME
        for i, ev in enumerate(self._events):
            rel_t = ev.t - self._first_t
            if rel_t > current_t:
                break
            if rel_t < window_start or ev.action != "mouse_down":
                continue

            button = ev.args[0].name if hasattr(ev.args[0], "name") else str(ev.args[0])
            color = BUTTON_COLORS.get(button, QColor("gray"))
            pos = self._position_at(rel_t)
            if pos is None:
                continue

            age = current_t - rel_t
            progress = age / RIPPLE_LIFETIME
            is_double = i in self._double_clicks
            max_r = RIPPLE_MAX_RADIUS_DOUBLE if is_double else RIPPLE_MAX_RADIUS
            self._add(pos, max_r * progress, 1.0 - progress, color, is_double)

    def clear(self) -> None:
        """Remove all ripple items from the scene."""
        self._clear()

    def _add(
        self,
        pos: tuple[int, int],
        radius: float,
        opacity: float,
        color: QColor,
        is_double: bool,
    ) -> None:
        """Add one ripple item to the scene.

        :param pos: Center of the ripple in scene units.
        :param radius: Current radius in scene units.
        :param opacity: Alpha factor in ``[0, 1]``.
        :param color: Base color, from :data:`BUTTON_COLORS`.
        :param is_double: Whether to draw a thicker ring (double click).
        """
        item = QGraphicsEllipseItem(-radius, -radius, radius * 2, radius * 2)
        item.setPos(pos[0], pos[1])
        color_alpha = QColor(color)
        color_alpha.setAlphaF(opacity)
        item.setPen(QPen(color_alpha, 6 if is_double else 3))
        item.setBrush(QBrush(Qt.NoBrush))
        item.setZValue(999)
        self._scene.addItem(item)
        self._items.append(item)

    def _clear(self) -> None:
        """Remove all ripple items from the scene."""
        for item in self._items:
            self._scene.removeItem(item)
        self._items.clear()
