"""Where a frozen capture is drawn on a screen, and which of its pixels lies under a point; without Qt widgets."""

import math

from PySide6.QtCore import QPointF, QRectF


def fit_capture(width: int, height: int, screen: QRectF) -> QRectF:
    """Rectangle showing a capture of this size whole and centred on a screen, never enlarged; e.g. a VNC screen."""
    scale = min(screen.width() / width, screen.height() / height, 1.0)
    shown_width, shown_height = width * scale, height * scale
    left = screen.left() + (screen.width() - shown_width) / 2
    top = screen.top() + (screen.height() - shown_height) / 2
    return QRectF(left, top, shown_width, shown_height)


def pixel_at(point: QPointF, shown: QRectF, width: int, height: int) -> tuple[int, int]:
    """Pixel of a capture of this size drawn in shown under a point, kept inside the capture."""
    x = math.floor((point.x() - shown.left()) * width / shown.width())
    y = math.floor((point.y() - shown.top()) * height / shown.height())
    return min(max(x, 0), width - 1), min(max(y, 0), height - 1)


def pixel_rect(left: int, top: int, right: int, bottom: int, shown: QRectF, width: int, height: int) -> QRectF:
    """Rectangle of pixels of a capture drawn in shown, edges between pixels, in coordinates of the screen."""
    x_scale, y_scale = shown.width() / width, shown.height() / height
    return QRectF(
        shown.left() + left * x_scale,
        shown.top() + top * y_scale,
        (right - left) * x_scale,
        (bottom - top) * y_scale,
    )
