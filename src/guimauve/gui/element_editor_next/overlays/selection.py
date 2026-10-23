"""Window covering a screen with its frozen capture, to select an area or a point of it."""

from enum import Enum

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QApplication, QWidget

from guimauve.gui.element_editor_next.canvas import region as regions
from guimauve.gui.element_editor_next.canvas.region import Region
from guimauve.gui.element_editor_next.components.magnifier import label_height, magnifier_rect, paint_magnifier
from guimauve.gui.element_editor_next.overlays.geometry import pixel_at, pixel_rect
from guimauve.gui.element_editor_next.theme import SEMANTIC, TYPE

SHADE = QColor(0, 0, 0, 110)
LIGHT_SHADE = QColor(0, 0, 0, 50)
"""Over the whole capture until a rectangle is drawn, telling it is frozen without hiding it."""
WHITE = QColor("#FFFFFF")
OUTSIDE = QColor("#000000")
"""Background around a capture smaller than its screen, and in the magnifier beyond the capture."""
BANNER_TOP = 24.0
BANNER_PADDING = QPointF(14, 7)
LABEL_PADDING = QPointF(6, 2)
LABEL_GAP = 14.0
NUMBER_SIZE = 120.0
NUMBER_FONT = 64
RADIUS = 8.0
HELP = {
    "area": "Drag to select an area. Hold Ctrl to move it. Esc to cancel.",
    "point": "Click a point. Esc to cancel.",
}


class SelectionMode(Enum):
    AREA = "area"
    POINT = "point"


class SelectionOverlay(QWidget):
    """Frozen capture of one screen, drawn pixel for pixel, or fitted when it is remote; the outside is shaded.

    In the AREA mode, a drag draws a rectangle, Ctrl held moving it instead, and its release selects it; a click
    without drag does nothing. In the POINT mode, a click selects the pixel. A magnifier follows the cursor, the
    size of the rectangle shows beside it, and a banner at the top tells what to do. Esc cancels. The rectangle and
    the point are pixels of the capture, physical for a local screen.

    :param image: Capture of the screen.
    :param shown: Where the capture is drawn, in coordinates of the window; the whole window by default.
    :param note: Added to the help of the banner, e.g. the scale of a remote screen.
    """

    selected = Signal()
    cancelled = Signal()
    drag_started = Signal()

    def __init__(
        self,
        image: QImage,
        mode: SelectionMode,
        shown: QRectF | None = None,
        note: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._image = image
        self._mode = mode
        self._shown = shown
        self._note = note
        self._number: int | None = None
        self._number_visible = False
        self._press: tuple[int, int] | None = None  # pixel where the button went down
        self._last: tuple[int, int] | None = None  # pixel of the last move, to move the rectangle with Ctrl
        self._dragging = False
        self._region: Region | None = None
        self._point: tuple[int, int] | None = None
        self._pointer: QPointF | None = None
        self._start = QPointF()  # point where the button went down, to tell a click from a drag
        self._font = QFont(QApplication.font())
        self._font.setPixelSize(TYPE.small)
        self._font.setWeight(QFont.Weight(TYPE.medium))
        self._font.setFeature(QFont.Tag("tnum"), 1)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # Result

    def region(self) -> Region | None:
        """Rectangle selected, or being drawn, in pixels of the capture."""
        return self._region

    def point(self) -> tuple[int, int] | None:
        """Pixel selected in the POINT mode."""
        return self._point

    def show_number(self, number: int | None) -> None:
        """Shows the number of the screen in large at its centre, or nothing."""
        self._number = number
        self._number_visible = number is not None
        self.update()

    def shows_number(self) -> bool:
        return self._number_visible

    @property
    def note(self) -> str | None:
        return self._note

    def hide_number(self) -> None:
        self._number_visible = False
        self.update()

    def shown_rect(self) -> QRectF:
        return QRectF(self.rect()) if self._shown is None else self._shown

    # Events

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press = self._last = self._pixel(event.position())
        self._dragging = False
        self._start = event.position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._pointer = event.position()
        if self._press is not None and self._mode is SelectionMode.AREA:
            moved = (event.position() - self._start).manhattanLength() >= QApplication.startDragDistance()
            if moved and not self._dragging:
                self._dragging = True
                self.drag_started.emit()
            if self._dragging:
                self._drag(self._pixel(event.position()), bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        pixel, dragging = self._pixel(event.position()), self._dragging
        self._press = self._last = None
        self._dragging = False
        if self._mode is SelectionMode.POINT:
            self._point = pixel
            self.selected.emit()
        elif dragging and self._region is not None:
            self.selected.emit()
        self.update()

    def leaveEvent(self, event: QEvent) -> None:
        self._pointer = None
        self.update()
        super().leaveEvent(event)

    # Painting

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), OUTSIDE)
        shown = self.shown_rect()
        painter.drawImage(shown, self._image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        shade = QPainterPath()
        shade.addRect(QRectF(self.rect()))
        if self._region is not None:
            selection = self._pixel_rect(self._region)
            inside = QPainterPath()
            inside.addRect(selection)
            shade = shade.subtracted(inside)
        painter.fillPath(shade, SHADE if self._region is not None else LIGHT_SHADE)
        if self._region is not None:
            painter.setPen(QPen(QColor(SEMANTIC.area), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._pixel_rect(self._region))
        if self._number_visible and self._number is not None:
            self._paint_number(painter)
        self._paint_banner(painter)
        if self._pointer is not None:
            pixel = self._pixel(self._pointer)
            where = magnifier_rect(self._pointer, QRectF(self.rect()), label_height(self._font))
            paint_magnifier(painter, self._image, QPoint(*pixel), where, OUTSIDE, self._font)
            if self._region is not None and self._dragging:
                self._paint_size(painter)
        painter.end()

    def _paint_banner(self, painter: QPainter) -> None:
        text = HELP[self._mode.value] if self._note is None else f"{HELP[self._mode.value]} {self._note}"
        metrics = QFontMetricsF(self._font)
        width = metrics.horizontalAdvance(text) + 2 * BANNER_PADDING.x()
        height = metrics.height() + 2 * BANNER_PADDING.y()
        banner = QRectF((self.width() - width) / 2, BANNER_TOP, width, height)
        _pill(painter, banner, text, self._font, BANNER_PADDING)

    def _paint_size(self, painter: QPainter) -> None:
        assert self._region is not None and self._pointer is not None
        text = f"{self._region.width} × {self._region.height} px"
        metrics = QFontMetricsF(self._font)
        width = metrics.horizontalAdvance(text) + 2 * LABEL_PADDING.x()
        height = metrics.height() + 2 * LABEL_PADDING.y()
        x, y = self._pointer.x() - width - LABEL_GAP, self._pointer.y() + LABEL_GAP  # left of the magnifier
        if x < 0:
            x = self._pointer.x() + LABEL_GAP
        _pill(painter, QRectF(x, min(y, self.height() - height), width, height), text, self._font, LABEL_PADDING)

    def _paint_number(self, painter: QPainter) -> None:
        font = QFont(self._font)
        font.setPixelSize(NUMBER_FONT)
        font.setWeight(QFont.Weight(TYPE.bold))
        box = QRectF(0, 0, NUMBER_SIZE, NUMBER_SIZE)
        box.moveCenter(QRectF(self.rect()).center())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(SEMANTIC.label))
        painter.drawRoundedRect(box, 2 * RADIUS, 2 * RADIUS)
        painter.setFont(font)
        painter.setPen(WHITE)
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, str(self._number))

    # Internals

    def _drag(self, pixel: tuple[int, int], move: bool) -> None:
        assert self._press is not None and self._last is not None
        width, height = self._image.width(), self._image.height()
        if move and self._region is not None:
            moved = regions.move(self._region, pixel[0] - self._last[0], pixel[1] - self._last[1], width, height)
            dx, dy = moved.left - self._region.left, moved.top - self._region.top
            self._press = (self._press[0] + dx, self._press[1] + dy)  # the corner held moves along
            self._region = moved
        else:
            self._region = regions.drawn(self._press, pixel, width, height)
        self._last = pixel

    def _pixel(self, point: QPointF) -> tuple[int, int]:
        return pixel_at(point, self.shown_rect(), self._image.width(), self._image.height())

    def _pixel_rect(self, region: Region) -> QRectF:
        image = self._image
        rect = self.shown_rect()
        return pixel_rect(region.left, region.top, region.right, region.bottom, rect, image.width(), image.height())


def _pill(painter: QPainter, rect: QRectF, text: str, font: QFont, padding: QPointF) -> None:
    metrics = QFontMetricsF(font)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(SEMANTIC.label))
    painter.drawRoundedRect(rect, RADIUS, RADIUS)
    painter.setFont(font)
    painter.setPen(WHITE)
    painter.drawText(QPointF(rect.x() + padding.x(), rect.y() + (rect.height() + metrics.capHeight()) / 2), text)
