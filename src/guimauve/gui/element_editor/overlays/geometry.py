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


def banner_rect(size: tuple[float, float], screen: QRectF, margin: float, avoid: QRectF | None) -> QRectF:
    """Banner centred at the top of a screen, or at the bottom when it would cover what to avoid, e.g. the cursor."""
    width, height = size
    top = QRectF(screen.left() + (screen.width() - width) / 2, screen.top() + margin, width, height)
    if avoid is None or not top.intersects(avoid):
        return top
    return top.translated(0, screen.height() - 2 * margin - height)


def number_rect(side: float, screen: QRectF, margin: float, avoid: QRectF | None) -> QRectF:
    """Square in the middle of a screen, or in its bottom left corner when it would cover what to avoid."""
    box = QRectF(0, 0, side, side)
    box.moveCenter(screen.center())
    if avoid is not None and box.intersects(avoid):
        box.moveTopLeft(QPointF(screen.left() + margin, screen.bottom() - margin - side))
    return box


def least_covering(places: list[QRectF], obstacles: list[QRectF]) -> QRectF:
    """The first place covering none of the obstacles, else the one covering the least of them."""

    def covered(place: QRectF) -> float:
        return sum(place.intersected(obstacle).width() * place.intersected(obstacle).height() for obstacle in obstacles)

    return next((place for place in places if covered(place) == 0), min(places, key=covered))


def corners(side: float, screen: QRectF, margin: float) -> list[QRectF]:
    """A square in each corner of a screen: bottom left first, then bottom right, top left and top right."""
    left, right = screen.left() + margin, screen.right() - margin - side
    top, bottom = screen.top() + margin, screen.bottom() - margin - side
    return [QRectF(x, y, side, side) for x, y in ((left, bottom), (right, bottom), (left, top), (right, top))]
