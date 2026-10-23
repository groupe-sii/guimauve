import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from guimauve.gui.element_editor_next.components.magnifier import (
    CELL,
    DIAMETER,
    GAP,
    PIXELS,
    label_height,
    magnifier_rect,
    paint_magnifier,
)
from guimauve.gui.element_editor_next.services.images import to_qimage

BOUNDS = QRectF(0, 0, 800, 600)
LABEL = 20.0


@pytest.mark.parametrize(
    ("cursor", "expected"),
    [
        (QPointF(100, 100), QPointF(100 + GAP, 100 + GAP)),  # below right
        (QPointF(750, 100), QPointF(750 - GAP - DIAMETER, 100 + GAP)),  # left near the right edge
        (QPointF(100, 550), QPointF(100 + GAP, 550 - GAP - DIAMETER - 6 - LABEL)),  # above near the bottom
    ],
)
def test_magnifier_stays_inside(cursor, expected):
    assert magnifier_rect(cursor, BOUNDS, LABEL).topLeft() == expected


def test_paints_the_pixels_around_the_aimed_one(qapp):
    array = np.zeros((40, 40, 3), np.uint8)
    array[20, 20] = (200, 10, 10)  # aimed at
    array[20, 21] = (10, 200, 10)  # its right neighbour
    canvas = QImage(200, 200, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#000000"))
    rect = QRectF(20, 20, DIAMETER, DIAMETER)
    font = QFont()
    font.setPixelSize(11)

    painter = QPainter(canvas)
    paint_magnifier(painter, to_qimage(array), QPoint(20, 20), rect, QColor("#0000FF"), font)
    painter.end()

    middle = rect.center()
    assert canvas.pixelColor(middle.toPoint()).name() == "#c80a0a"
    assert canvas.pixelColor(QPointF(middle.x() + CELL, middle.y()).toPoint()).name() == "#0ac80a"


def test_outside_of_the_image_in_the_outside_color(qapp):
    canvas = QImage(200, 200, QImage.Format.Format_RGB32)
    canvas.fill(QColor("#000000"))
    rect = QRectF(20, 20, DIAMETER, DIAMETER)

    painter = QPainter(canvas)
    paint_magnifier(painter, to_qimage(np.zeros((40, 40, 3), np.uint8)), QPoint(0, 0), rect, QColor("#0000FF"), QFont())
    painter.end()

    left_of_the_image = QPointF(rect.x() + 3.5 * CELL, rect.y() + (PIXELS // 2 + 0.5) * CELL)  # centre of a cell
    assert canvas.pixelColor(left_of_the_image.toPoint()).name() == "#0000ff"


def test_label_height_follows_the_font(qapp):
    small, large = QFont(), QFont()
    small.setPixelSize(10)
    large.setPixelSize(20)

    assert label_height(large) > label_height(small)
