"""Floating preview of a match: the capture around it, its outline and the point a run would click."""

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager

WHITE = "#FFFFFF"
ARM = 7.0
"""Length of each arm of the crosshair, in screen pixels."""
GAP = 3.0


class MatchPreview(QWidget):
    """Window above the others, without focus, showing a part of a capture at its real size, edge to edge.

    The match is outlined in a solid line when a run would use it, dashed otherwise, with a crosshair on the point
    it would click. A part larger than the preview is reduced, the percentage in a corner.
    """

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._theme = theme
        self._image = QImage()
        self._box: list[QPointF] = []
        self._target = QPointF()
        self._used = False
        self._scale = 1.0

    @property
    def scale(self) -> float:
        """Size of the image shown over its real size, at most 1."""
        return self._scale

    def show_match(
        self, image: QImage, box: list[tuple[int, int]], target: tuple[int, int], used: bool, below: QRect
    ) -> None:
        """Shows a part of a capture above a rectangle of the screen, or under it when there is no room above.

        :param box: Corners of the match in the image; empty without a box.
        :param target: Point a run would click, in the image.
        :param below: Global rectangle the preview must not cover, such as the row of the match.
        """
        self._image = image
        self._box = [QPointF(x, y) for x, y in box]
        self._target = QPointF(*target)
        self._used = used
        self._scale = min(1.0, METRICS.preview_width / image.width(), METRICS.preview_height / image.height())
        self.resize(round(image.width() * self._scale), round(image.height() * self._scale))
        self.move(_place(self.width(), self.height(), below, self.screen().availableGeometry()))
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        palette = self._theme.palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        radius = METRICS.radius_control
        outline = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), radius, radius)
        painter.save()
        painter.setClipPath(clip)
        painter.scale(self._scale, self._scale)
        painter.drawImage(0, 0, self._image)
        painter.restore()

        accent = QColor(palette.accent)
        corners = [point * self._scale for point in self._box]
        if corners:
            style = Qt.PenStyle.SolidLine if self._used else Qt.PenStyle.DashLine
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(accent, 2 if self._used else 1.5, style))
            painter.drawPolygon(QPolygonF(corners))
        self._crosshair(painter, self._target * self._scale, accent)

        if self._scale < 1:
            text = f"{round(self._scale * 100)} %"
            metrics = painter.fontMetrics()
            pill = QRectF(0, 0, metrics.horizontalAdvance(text) + 2 * METRICS.space(1), metrics.height())
            pill.moveTopRight(QPointF(self.width() - METRICS.space(1), METRICS.space(1)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(palette.surface))
            painter.drawRoundedRect(pill, 4, 4)
            painter.setPen(QColor(palette.text_secondary))
            painter.drawText(pill, Qt.AlignmentFlag.AlignCenter, text)

        painter.setPen(QPen(QColor(palette.border_strong), 1))  # over the image, so its corners stay round
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(outline, radius, radius)

    def _crosshair(self, painter: QPainter, at: QPointF, color: QColor) -> None:
        arms = [
            (QPointF(-GAP - ARM, 0), QPointF(-GAP, 0)),
            (QPointF(GAP, 0), QPointF(GAP + ARM, 0)),
            (QPointF(0, -GAP - ARM), QPointF(0, -GAP)),
            (QPointF(0, GAP), QPointF(0, GAP + ARM)),
        ]
        round_cap, solid = Qt.PenCapStyle.RoundCap, Qt.PenStyle.SolidLine
        for pen in (QPen(QColor(WHITE), 4, solid, round_cap), QPen(color, 2, solid, round_cap)):
            painter.setPen(pen)
            for start, end in arms:
                painter.drawLine(at + start, at + end)


def _place(width: int, height: int, below: QRect, room: QRect) -> QPoint:
    """Above the rectangle, left aligned with it, or under it without room above; always inside the room."""
    gap = METRICS.space(1)
    y = below.top() - gap - height
    if y < room.top():
        y = below.bottom() + gap
    x = min(max(below.left(), room.left()), room.right() - width)
    return QPoint(x, max(min(y, room.bottom() - height), room.top()))
