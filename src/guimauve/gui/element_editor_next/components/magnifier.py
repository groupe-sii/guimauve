"""Round magnifier showing the pixels around the one aimed at, with its coordinates; drawn by the widget using it."""

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen

from guimauve.gui.element_editor_next.theme import SEMANTIC

DIAMETER = 120.0
PIXELS = 15
"""Pixels across the magnifier, an odd number so the one aimed at is in the middle."""
CELL = DIAMETER / PIXELS
GAP = 20.0
"""Distance from the cursor to the magnifier."""
LABEL_GAP = 6.0
LABEL_PADDING = QPointF(6, 2)
LABEL_RADIUS = 5.0
GRID = QColor(0, 0, 0, 31)
WHITE = QColor("#FFFFFF")


def magnifier_rect(cursor: QPointF, bounds: QRectF, label_height: float) -> QRectF:
    """Where the magnifier goes: below and right of the cursor, or on the other side where it would leave bounds."""
    height = DIAMETER + LABEL_GAP + label_height
    x = cursor.x() + GAP
    if x + DIAMETER > bounds.right():
        x = cursor.x() - GAP - DIAMETER
    y = cursor.y() + GAP
    if y + height > bounds.bottom():
        y = cursor.y() - GAP - height
    return QRectF(x, y, DIAMETER, DIAMETER)


def label_height(font: QFont) -> float:
    return QFontMetricsF(font).height() + 2 * LABEL_PADDING.y()


def paint_magnifier(
    painter: QPainter, image: QImage, pixel: QPoint, rect: QRectF, outside: QColor, font: QFont
) -> None:
    """Paints the pixels around pixel in the circle of rect, the outside of the image in the outside color.

    The pixel aimed at is framed in the middle; its coordinates show in a label under the circle.
    """
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    circle = QPainterPath()
    circle.addEllipse(rect)
    painter.setClipPath(circle)
    painter.fillRect(rect, outside)
    half = PIXELS // 2
    for row in range(PIXELS):
        for column in range(PIXELS):
            x, y = pixel.x() - half + column, pixel.y() - half + row
            if image.valid(x, y):
                cell = QRectF(rect.x() + column * CELL, rect.y() + row * CELL, CELL, CELL)
                painter.fillRect(cell, image.pixelColor(x, y))
    painter.setPen(QPen(GRID, 1))
    for index in range(1, PIXELS):
        painter.drawLine(QPointF(rect.x() + index * CELL, rect.top()), QPointF(rect.x() + index * CELL, rect.bottom()))
        painter.drawLine(QPointF(rect.left(), rect.y() + index * CELL), QPointF(rect.right(), rect.y() + index * CELL))
    middle = QRectF(rect.x() + half * CELL, rect.y() + half * CELL, CELL, CELL)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(SEMANTIC.label), 3))
    painter.drawRect(middle.adjusted(-1.5, -1.5, 1.5, 1.5))
    painter.setPen(QPen(WHITE, 1.5))
    painter.drawRect(middle.adjusted(-0.75, -0.75, 0.75, 0.75))
    painter.setClipping(False)

    painter.setPen(QPen(WHITE, 3))
    painter.drawEllipse(rect.adjusted(-1.5, -1.5, 1.5, 1.5))
    painter.setPen(QPen(QColor(SEMANTIC.image_border), 1))
    painter.drawEllipse(rect.adjusted(-3.5, -3.5, 3.5, 3.5))

    text = f"x {pixel.x()}, y {pixel.y()}"
    metrics = QFontMetricsF(font)
    width = metrics.horizontalAdvance(text) + 2 * LABEL_PADDING.x()
    label = QRectF(rect.center().x() - width / 2, rect.bottom() + LABEL_GAP, width, label_height(font))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(SEMANTIC.label))
    painter.drawRoundedRect(label, LABEL_RADIUS, LABEL_RADIUS)
    painter.setFont(font)
    painter.setPen(WHITE)
    baseline = label.y() + (label.height() + metrics.capHeight()) / 2
    painter.drawText(QPointF(label.x() + LABEL_PADDING.x(), baseline), text)
    painter.restore()
