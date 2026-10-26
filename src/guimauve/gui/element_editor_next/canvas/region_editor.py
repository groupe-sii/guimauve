"""Editing of a rectangle on the image by the canvas view, for the match area or a crop."""

import math
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen

from guimauve.gui.element_editor_next.canvas import region as regions
from guimauve.gui.element_editor_next.canvas.region import Grip, Region
from guimauve.gui.element_editor_next.theme import SEMANTIC

if TYPE_CHECKING:
    from guimauve.gui.element_editor_next.canvas.view import CanvasView

HANDLE = 8.0
"""Side of a handle, in pixels of the view."""
REACH = 6.0
"""Distance from a handle at which it is grabbed."""
SHADE = QColor(0, 0, 0, 115)
WHITE = QColor("#FFFFFF")
LABEL_GAP = 6.0
LABEL_PADDING = QPointF(6, 2)
LABEL_RADIUS = 5.0
CURSORS = {
    Grip.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    Grip.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    Grip.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    Grip.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    Grip.TOP: Qt.CursorShape.SizeVerCursor,
    Grip.BOTTOM: Qt.CursorShape.SizeVerCursor,
    Grip.LEFT: Qt.CursorShape.SizeHorCursor,
    Grip.RIGHT: Qt.CursorShape.SizeHorCursor,
    Grip.INSIDE: Qt.CursorShape.SizeAllCursor,
    Grip.OUTSIDE: Qt.CursorShape.CrossCursor,
}


class RegionEditor(QObject):
    """Rectangle with eight handles: a handle resizes it, the inside moves it, the outside draws a new one.

    The rectangle stays on whole pixels inside the image; the outside of the image is shaded around it, and its
    size shows above it.
    """

    changed = Signal()

    def __init__(self, view: "CanvasView", font: QFont):
        super().__init__(view)
        self._view = view
        self._font = font
        self._region: Region | None = None
        self._grip: Grip | None = None
        self._from: Region | None = None  # rectangle when the drag started
        self._start: QPointF | None = None  # point of the image where the drag started

    @property
    def region(self) -> Region | None:
        return self._region

    def start(self, region: Region) -> None:
        self._region = region
        self._grip = None
        self.changed.emit()

    def stop(self) -> None:
        self._region = self._grip = None
        self.changed.emit()

    def is_dragging(self) -> bool:
        return self._grip is not None

    # Mouse, in points of the viewport

    def grip_at(self, point: QPointF) -> Grip:
        assert self._region is not None
        for grip, (x, y) in regions.handle_points(self._region).items():
            handle = self._to_view(QPointF(x, y))
            if abs(handle.x() - point.x()) <= REACH and abs(handle.y() - point.y()) <= REACH:
                return grip
        if self.view_rect().contains(point):
            return Grip.INSIDE
        return Grip.OUTSIDE

    def cursor_at(self, point: QPointF) -> Qt.CursorShape:
        return CURSORS[self._grip or self.grip_at(point)]

    def press(self, point: QPointF) -> None:
        self._grip = self.grip_at(point)
        self._from = self._region
        self._start = self._view.to_image(point)

    def move(self, point: QPointF) -> None:
        if self._grip is None or self._from is None or self._start is None:
            return
        width, height = self._size()
        position = self._view.to_image(point)
        if self._grip is Grip.INSIDE:
            dx, dy = round(position.x() - self._start.x()), round(position.y() - self._start.y())
            region = regions.move(self._from, dx, dy, width, height)
        elif self._grip is Grip.OUTSIDE:
            start = (math.floor(self._start.x()), math.floor(self._start.y()))
            region = regions.drawn(start, (math.floor(position.x()), math.floor(position.y())), width, height)
        else:
            region = regions.resize(self._from, self._grip, position.x(), position.y(), width, height)
        if region != self._region:
            self._region = region
            self.changed.emit()

    def release(self) -> None:
        self._grip = self._from = self._start = None

    # Painting, in points of the viewport

    def view_rect(self) -> QRectF:
        assert self._region is not None
        region = self._region
        return self._view.viewportTransform().mapRect(QRectF(region.left, region.top, region.width, region.height))

    def paint(self, painter: QPainter) -> None:
        if self._region is None:
            return
        width, height = self._size()
        image = self._view.viewportTransform().mapRect(QRectF(0, 0, width, height))
        rect = self.view_rect()
        shade = QPainterPath()
        shade.addRect(image)
        inside = QPainterPath()
        inside.addRect(rect)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillPath(shade.subtracted(inside), SHADE)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(SEMANTIC.area), 2))
        painter.drawRect(rect)
        painter.setBrush(WHITE)
        for x, y in regions.handle_points(self._region).values():
            centre = self._to_view(QPointF(x, y))
            painter.drawRect(QRectF(centre.x() - HANDLE / 2, centre.y() - HANDLE / 2, HANDLE, HANDLE))
        self._paint_size(painter, rect)
        painter.restore()

    def _paint_size(self, painter: QPainter, rect: QRectF) -> None:
        assert self._region is not None
        text = f"{self._region.width} × {self._region.height} px"
        metrics = QFontMetricsF(self._font)
        label = QRectF(
            rect.left(),
            rect.top() - LABEL_GAP - HANDLE / 2 - metrics.height() - 2 * LABEL_PADDING.y(),
            metrics.horizontalAdvance(text) + 2 * LABEL_PADDING.x(),
            metrics.height() + 2 * LABEL_PADDING.y(),
        )
        if label.top() < 0:  # no room above: inside, at the top left
            label.moveTopLeft(QPointF(rect.left() + LABEL_GAP, rect.top() + LABEL_GAP))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(SEMANTIC.label))
        painter.drawRoundedRect(label, LABEL_RADIUS, LABEL_RADIUS)
        painter.setFont(self._font)
        painter.setPen(WHITE)
        baseline = label.y() + (label.height() + metrics.capHeight()) / 2
        painter.drawText(QPointF(label.x() + LABEL_PADDING.x(), baseline), text)

    def _to_view(self, point: QPointF) -> QPointF:
        return self._view.viewportTransform().map(point)

    def _size(self) -> tuple[int, int]:
        image = self._view.image()
        assert image is not None, "a rectangle is edited on an image"
        return image.width(), image.height()
