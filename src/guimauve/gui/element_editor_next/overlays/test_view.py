"""Window covering a screen with the capture a test searched, and what the test found on it."""

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QApplication, QWidget

from guimauve.gui.element_editor_next.overlays.geometry import banner_rect, number_rect, pixel_rect
from guimauve.gui.element_editor_next.overlays.selection import (
    ACCENT,
    BANNER_MARGIN,
    BANNER_PADDING,
    BANNER_RADIUS,
    LABEL_PADDING,
    NUMBER_FONT,
    NUMBER_SIZE,
    OUTSIDE,
    RADIUS,
    SHADE,
    WHITE,
)
from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.gui.element_editor_next.theme import LIGHT, SEMANTIC, TYPE

KEYS = "Esc or click to close"
NOT_SEARCHED = "Not searched"
CODE = "{ }"
CODE_COLOR = QColor(LIGHT.inherit)
"""The values of the code are violet in the editor; their search area too."""
HALO = QColor(LIGHT.accent).lighter(170)
ARM, GAP = 9.0, 4.0


@dataclass(frozen=True)
class ViewMatch:
    """A match as the full screen draws it, in pixels of the capture of its screen.

    :param index: Index of the match in the report; its number on screen is index + 1.
    :param box: Corners of the match; empty without a box, as a fixed position.
    """

    index: int
    box: tuple[tuple[int, int], ...]
    target: tuple[int, int]
    used: bool


@dataclass(frozen=True)
class ScreenView:
    """What the full screen draws over the capture of one screen.

    :param number: Number of the screen in the driver.
    :param searched: Whether the test searched this screen; the screens it did not are shaded whole.
    :param area: Search area in the capture as (left, top, right, bottom), outside shaded; None for the whole capture.
    :param code_area: Search area set in the code, outlined, when it applies; None otherwise.
    """

    number: int
    image: np.ndarray
    searched: bool
    area: tuple[int, int, int, int] | None
    code_area: tuple[int, int, int, int] | None
    matches: tuple[ViewMatch, ...]


class TestView(QWidget):
    """Capture of one screen as the test searched it, drawn pixel for pixel, or fitted when it is remote.

    Outside the search area is shaded, a screen the test did not search shaded whole. The search area set in the
    code is dashed and marked with braces. Matches are numbered as in the results: the one a run would use solid with
    a crosshair on its click point, the others dashed, their click point shown under the cursor. The focused match
    has a halo. A banner says what the test found; Esc or a click closes.

    :param shown: Where the capture is drawn, in coordinates of the window; the whole window by default.
    :param focused: Index of the match to show with a halo, if any.
    """

    __test__ = False  # not a test class for pytest

    closed = Signal()

    def __init__(
        self,
        view: ScreenView,
        title: str,
        shown: QRectF | None = None,
        focused: int | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._view = view
        self._image = to_qimage(view.image)
        self._title = title
        self._shown = shown
        self._focused = focused
        self._hovered: int | None = None
        self._number: int | None = None
        self._font = QFont(QApplication.font())
        self._font.setPixelSize(TYPE.small)
        self._font.setWeight(QFont.Weight(TYPE.medium))
        self._font.setFeature(QFont.Tag("tnum"), 1)
        self._title_font = QFont(self._font)
        self._title_font.setPixelSize(TYPE.title)
        self._title_font.setWeight(QFont.Weight(TYPE.bold))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def show_number(self, number: int | None) -> None:
        """Shows the number of the screen in the bottom left corner, when there are several."""
        self._number = number
        self.update()

    @property
    def focused(self) -> int | None:
        """Index of the match shown with a halo, if any."""
        return self._focused

    @property
    def hovered(self) -> int | None:
        """Index of the match under the cursor, whose click point shows."""
        return self._hovered

    def shown_rect(self) -> QRectF:
        return self._shown if self._shown is not None else QRectF(self.rect())

    # Events

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.closed.emit()
            return
        super().keyPressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.closed.emit()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        hovered = next(
            (
                m.index
                for m in self._view.matches
                if self._polygon(m).containsPoint(event.position(), Qt.FillRule.OddEvenFill)
            ),
            None,
        )
        if hovered != self._hovered:
            self._hovered = hovered
            self.update()

    # Painting

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), OUTSIDE)
        painter.drawImage(self.shown_rect(), self._image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_shade(painter)
        if self._view.code_area is not None:
            self._paint_code_area(painter, self._view.code_area)
        for match in self._view.matches:
            self._paint_match(painter, match)
        if self._number is not None:
            self._paint_number(painter)
        self._paint_banner(painter)
        painter.end()

    def banner_rect(self) -> QRectF:
        title, keys = QFontMetricsF(self._title_font), QFontMetricsF(self._font)
        width = max(title.horizontalAdvance(self._title), keys.horizontalAdvance(KEYS)) + 2 * BANNER_PADDING.x()
        height = title.height() + keys.height() + 2 * BANNER_PADDING.y()
        return banner_rect((width, height), QRectF(self.rect()), BANNER_MARGIN, None)

    def _paint_shade(self, painter: QPainter) -> None:
        view = self._view
        shade = QPainterPath()
        shade.addRect(QRectF(self.rect()))
        if view.searched and view.area is not None:
            inside = QPainterPath()
            inside.addRect(self._rect(view.area))
            shade = shade.subtracted(inside)
        if not view.searched or view.area is not None:
            painter.fillPath(shade, SHADE)
        if not view.searched:
            font = QFont(self._title_font)
            painter.setFont(font)
            painter.setPen(WHITE)
            painter.drawText(QRectF(self.rect()), Qt.AlignmentFlag.AlignCenter, NOT_SEARCHED)

    def _paint_code_area(self, painter: QPainter, area: tuple[int, int, int, int]) -> None:
        rect = self._rect(area)
        painter.setPen(QPen(CODE_COLOR, 1.5, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        metrics = QFontMetricsF(self._font)
        pill = QRectF(
            rect.left() + 6,
            rect.top() + 6,
            metrics.horizontalAdvance(CODE) + 2 * LABEL_PADDING.x(),
            metrics.height() + 2 * LABEL_PADDING.y(),
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(CODE_COLOR)
        painter.drawRoundedRect(pill, RADIUS, RADIUS)
        painter.setFont(self._font)
        painter.setPen(WHITE)
        painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, CODE)

    def _paint_match(self, painter: QPainter, match: ViewMatch) -> None:
        polygon = self._polygon(match)
        if match.box:
            if match.index == self._focused:
                painter.setPen(
                    QPen(HALO, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                )
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPolygon(polygon)
            style = Qt.PenStyle.SolidLine if match.used else Qt.PenStyle.DashLine
            painter.setPen(QPen(ACCENT, 3 if match.used else 2, style))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(polygon)
            self._paint_number_pill(painter, polygon.boundingRect().topLeft(), match)
        if match.used or match.index == self._hovered or not match.box:
            self._paint_crosshair(painter, self._point(match.target), thin=not match.used)

    def _paint_number_pill(self, painter: QPainter, corner: QPointF, match: ViewMatch) -> None:
        text = str(match.index + 1)
        metrics = QFontMetricsF(self._font)
        height = metrics.height() + 2 * LABEL_PADDING.y()
        width = max(metrics.horizontalAdvance(text) + 2 * LABEL_PADDING.x(), height)
        pill = QRectF(corner.x() - width / 2, corner.y() - height / 2, width, height)
        painter.setPen(QPen(ACCENT, 1.5))
        painter.setBrush(ACCENT if match.used else WHITE)
        painter.drawRoundedRect(pill, height / 2, height / 2)
        painter.setFont(self._font)
        painter.setPen(WHITE if match.used else ACCENT)
        painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_crosshair(self, painter: QPainter, at: QPointF, thin: bool) -> None:
        arms = [
            (QPointF(-GAP - ARM, 0), QPointF(-GAP, 0)),
            (QPointF(GAP, 0), QPointF(GAP + ARM, 0)),
            (QPointF(0, -GAP - ARM), QPointF(0, -GAP)),
            (QPointF(0, GAP), QPointF(0, GAP + ARM)),
        ]
        width = 1.5 if thin else 2.5
        cap, solid = Qt.PenCapStyle.RoundCap, Qt.PenStyle.SolidLine
        for pen in (QPen(WHITE, width + 2.5, solid, cap), QPen(ACCENT, width, solid, cap)):
            painter.setPen(pen)
            for start, end in arms:
                painter.drawLine(at + start, at + end)

    def _paint_number(self, painter: QPainter) -> None:
        font = QFont(self._font)
        font.setPixelSize(NUMBER_FONT)
        font.setWeight(QFont.Weight(TYPE.bold))
        box = number_rect(NUMBER_SIZE, QRectF(self.rect()), BANNER_MARGIN, QRectF(self.rect()))  # in the corner
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(SEMANTIC.label))
        painter.drawRoundedRect(box, 2 * RADIUS, 2 * RADIUS)
        painter.setFont(font)
        painter.setPen(WHITE)
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, str(self._number))

    def _paint_banner(self, painter: QPainter) -> None:
        banner = self.banner_rect()
        title = QFontMetricsF(self._title_font)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ACCENT)
        painter.drawRoundedRect(banner, BANNER_RADIUS, BANNER_RADIUS)
        left, top = banner.left() + BANNER_PADDING.x(), banner.top() + BANNER_PADDING.y()
        painter.setFont(self._title_font)
        painter.setPen(WHITE)
        painter.drawText(QPointF(left, top + title.ascent()), self._title)
        painter.setFont(self._font)
        painter.setPen(QColor(255, 255, 255, 210))
        painter.drawText(QPointF(left, top + title.height() + QFontMetricsF(self._font).ascent()), KEYS)

    # Coordinates

    def _rect(self, area: tuple[int, int, int, int]) -> QRectF:
        left, top, right, bottom = area
        return pixel_rect(left, top, right, bottom, self.shown_rect(), self._width(), self._height())

    def _point(self, pixel: tuple[int, int]) -> QPointF:
        shown = self.shown_rect()
        return QPointF(
            shown.left() + (pixel[0] + 0.5) * shown.width() / self._width(),
            shown.top() + (pixel[1] + 0.5) * shown.height() / self._height(),
        )

    def _polygon(self, match: ViewMatch) -> QPolygonF:
        shown = self.shown_rect()
        x_scale, y_scale = shown.width() / self._width(), shown.height() / self._height()
        return QPolygonF([QPointF(shown.left() + x * x_scale, shown.top() + y * y_scale) for x, y in match.box])

    def _width(self) -> int:
        return max(self._view.image.shape[1], 1)

    def _height(self) -> int:
        return max(self._view.image.shape[0], 1)
