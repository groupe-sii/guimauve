"""Cursor and scroll-arrow overlay on the preview canvas."""

from typing import Optional

from PySide6.QtCore import QPointF
from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsPolygonItem, QGraphicsScene


_CURSOR_SCALE = 2.2   # bump the arrow so it reads at scaled-down preview sizes

_CURSOR_POINTS = [
    QPointF(0 * _CURSOR_SCALE, 0 * _CURSOR_SCALE),
    QPointF(0 * _CURSOR_SCALE, 16 * _CURSOR_SCALE),
    QPointF(4 * _CURSOR_SCALE, 12 * _CURSOR_SCALE),
    QPointF(7 * _CURSOR_SCALE, 20 * _CURSOR_SCALE),
    QPointF(9 * _CURSOR_SCALE, 19 * _CURSOR_SCALE),
    QPointF(6 * _CURSOR_SCALE, 12 * _CURSOR_SCALE),
    QPointF(11 * _CURSOR_SCALE, 12 * _CURSOR_SCALE),
]

# Two stacked chevrons pointing up, à la Material Design "double chevron".
# Mirrored on the X axis for the down variant. Bigger and cleaner than a
# single arrow with a tail — reads well even at small canvas sizes.
_SCROLL_UP_POINTS = [
    # Top chevron
    QPointF(-18, -6), QPointF(0, -24), QPointF(18, -6),
    QPointF(12, 0),   QPointF(0, -12), QPointF(-12, 0),
    # Bottom chevron
    QPointF(-18, 14), QPointF(0, -4),  QPointF(18, 14),
    QPointF(12, 20),  QPointF(0, 8),   QPointF(-12, 20),
]
_SCROLL_DOWN_POINTS = [QPointF(p.x(), -p.y()) for p in _SCROLL_UP_POINTS]


class CursorRenderer:
    """Owns the cursor polygon and the scroll-arrow polygon.

    Only one of the two is visible at a time: the arrow replaces the
    cursor while a scroll batch is active, so the user sees direction
    rather than a still cursor.
    """

    def __init__(self, scene: QGraphicsScene) -> None:
        """
        :param scene: The scene both items are added to.
        """
        self._scene = scene
        self._cursor = self._build_cursor()
        self._arrow = self._build_arrow()

    def _build_cursor(self) -> QGraphicsPolygonItem:
        """:return: A white cursor polygon added to the scene, hidden."""
        item = QGraphicsPolygonItem(QPolygonF(_CURSOR_POINTS))
        item.setBrush(QBrush(QColor("white")))
        item.setPen(QPen(QColor("black"), 1))
        item.setZValue(1000)
        item.setVisible(False)
        self._scene.addItem(item)
        return item

    def _build_arrow(self) -> QGraphicsPolygonItem:
        """:return: An orange scroll-arrow polygon added to the scene, hidden."""
        item = QGraphicsPolygonItem(QPolygonF(_SCROLL_UP_POINTS))
        item.setBrush(QBrush(QColor("#EF9F27")))
        item.setPen(QPen(QColor("black"), 2))
        item.setZValue(1001)
        item.setVisible(False)
        self._scene.addItem(item)
        return item

    def render(
        self,
        pos: Optional[tuple[int, int]],
        scroll_dir: Optional[int],
    ) -> None:
        """Update visibility and position of the cursor / arrow.

        :param pos: Last known cursor position in scene units, or
            ``None`` when no ``mouse_move`` has happened yet at the
            current timestamp.
        :param scroll_dir: ``+1`` for scroll up, ``-1`` for scroll down,
            ``None`` outside any scroll batch.
        """
        if pos is None:
            self._cursor.setVisible(False)
            self._arrow.setVisible(False)
            return

        if scroll_dir is not None:
            self._cursor.setVisible(False)
            points = _SCROLL_DOWN_POINTS if scroll_dir < 0 else _SCROLL_UP_POINTS
            self._arrow.setPolygon(QPolygonF(points))
            self._arrow.setPos(pos[0], pos[1])
            self._arrow.setVisible(True)
        else:
            self._arrow.setVisible(False)
            self._cursor.setPos(pos[0], pos[1])
            self._cursor.setVisible(True)

    def hide(self) -> None:
        """Hide both the cursor and the scroll arrow."""
        self._cursor.setVisible(False)
        self._arrow.setVisible(False)