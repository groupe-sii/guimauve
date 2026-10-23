"""Crosshair of a target on the image, with its number, its name and its coordinates."""

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsSceneHoverEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from guimauve.gui.element_editor_next.theme import SEMANTIC, TYPE

WHITE = "#FFFFFF"
ARM_INNER, ARM_OUTER = 4.0, 12.0
"""Arms of the crosshair, from and to this distance of the pixel: its centre stays visible."""
HALO = 11.0
DOT = 1.8
PILL_HEIGHT = 15.0
PILL_RADIUS = 4.0
NUMBER_AT = QPointF(12, -22)
NAME_AT = QPointF(32, -24)
COORDINATES_AT = QPointF(14, 14)
LABEL_PADDING = QPointF(7, 2)
COORDINATES_PADDING = QPointF(6, 2)
LABEL_RADIUS = 5.0
HIT_RADIUS = ARM_OUTER + 2


@dataclass(frozen=True)
class TargetMarker:
    """What the canvas shows of a target.

    :param number: Position in the list of targets, from 1, as in the Variant tab; None for a single target.
    :param used: The target the variant clicks: the target property, or else the default target.
    :param outside: Outside the image, drawn in the warning color.
    """

    key: int
    number: int | None
    name: str | None
    x: int
    y: int
    used: bool = False
    selected: bool = False
    outside: bool = False


class TargetItem(QGraphicsItem):
    """Crosshair centred on the pixel of a target, the same size at every zoom.

    The target used is drawn solid and thick, the others dashed; the number, when there are several targets, sits in
    a pill filled for the target used. The name shows on hover or selection, the coordinates on selection, with a halo.
    """

    def __init__(self, marker: TargetMarker):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setAcceptHoverEvents(True)
        self._hovered = False
        self._marker = marker
        self._fonts = _fonts()
        self._rect = QRectF()
        self.set_marker(marker)

    @property
    def marker(self) -> TargetMarker:
        return self._marker

    def set_marker(self, marker: TargetMarker) -> None:
        self.prepareGeometryChange()
        self._marker = marker
        self.setPos(marker.x + 0.5, marker.y + 0.5)
        self.setZValue(2 if marker.selected else 1)
        self._rect = self._bounds()
        self.update()

    # Geometry

    def boundingRect(self) -> QRectF:
        return self._rect

    def shape(self) -> QPainterPath:
        """The crosshair and the number: what the mouse can grab."""
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), HIT_RADIUS, HIT_RADIUS)
        if self._marker.number is not None:
            path.addRect(self._number_rect())
        return path

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._hovered = False
        self.update()

    def is_hovered(self) -> bool:
        return self._hovered

    def shows_name(self) -> bool:
        return self._marker.name is not None and (self._hovered or self._marker.selected)

    # Painting

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        marker = self._marker
        color = QColor(SEMANTIC.warning if marker.outside else SEMANTIC.target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if marker.selected:
            halo = QColor(color)
            halo.setAlphaF(0.5)
            painter.setPen(QPen(halo, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), HALO, HALO)

        width = 2.5 if marker.used else 1.75
        painter.setPen(QPen(QColor(WHITE), width + 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        self._draw_arms(painter)
        pen = QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        if not marker.used:
            pen.setDashPattern([2 / width, 2 / width])  # 2 px dashes, in units of the pen width
        painter.setPen(pen)
        self._draw_arms(painter)
        painter.setPen(QPen(QColor(WHITE), 1))
        painter.setBrush(color)
        painter.drawEllipse(QPointF(0, 0), DOT, DOT)

        if marker.number is not None:
            number = self._number_rect()
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(color if marker.used else QColor(WHITE))
            painter.drawRoundedRect(number, PILL_RADIUS, PILL_RADIUS)
            _text(painter, self._fonts.number, number, str(marker.number), QColor(WHITE) if marker.used else color)

        if self.shows_name():
            name = self._name_rect()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(name, LABEL_RADIUS, LABEL_RADIUS)
            _text(painter, self._fonts.name, name, marker.name or "", QColor(WHITE))
        if marker.selected:
            coordinates = self._coordinates_rect()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(SEMANTIC.label))
            painter.drawRoundedRect(coordinates, LABEL_RADIUS, LABEL_RADIUS)
            _text(painter, self._fonts.coordinates, coordinates, self._coordinates(), QColor(WHITE))

    @staticmethod
    def _draw_arms(painter: QPainter) -> None:
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            painter.drawLine(QPointF(dx * ARM_INNER, dy * ARM_INNER), QPointF(dx * ARM_OUTER, dy * ARM_OUTER))

    # Parts

    def _coordinates(self) -> str:
        return f"x {self._marker.x}, y {self._marker.y}"

    def _number_rect(self) -> QRectF:
        text = str(self._marker.number or "")
        width = max(PILL_HEIGHT, QFontMetricsF(self._fonts.number).horizontalAdvance(text) + 6)
        return QRectF(NUMBER_AT.x(), NUMBER_AT.y(), width, PILL_HEIGHT)

    def _name_rect(self) -> QRectF:
        at = NAME_AT if self._marker.number is not None else QPointF(NUMBER_AT.x(), NAME_AT.y())  # in its place
        return _label_rect(at, self._fonts.name, self._marker.name or "", LABEL_PADDING)

    def _coordinates_rect(self) -> QRectF:
        return _label_rect(COORDINATES_AT, self._fonts.coordinates, self._coordinates(), COORDINATES_PADDING)

    def _bounds(self) -> QRectF:
        """Every part the item may draw, whether shown now or on hover, plus the width of the pens."""
        rect = QRectF(-ARM_OUTER, -ARM_OUTER, 2 * ARM_OUTER, 2 * ARM_OUTER)
        if self._marker.number is not None:
            rect = rect.united(self._number_rect())
        if self._marker.name is not None:
            rect = rect.united(self._name_rect())
        rect = rect.united(self._coordinates_rect())
        return rect.adjusted(-3, -3, 3, 3)


@dataclass(frozen=True)
class _Fonts:
    number: QFont
    name: QFont
    coordinates: QFont


def _fonts() -> _Fonts:
    def font(weight: int, tabular: bool = False) -> QFont:
        result = QFont(QApplication.font())
        result.setPixelSize(TYPE.caption)
        result.setWeight(QFont.Weight(weight))
        if tabular:
            result.setFeature(QFont.Tag("tnum"), 1)
        return result

    return _Fonts(font(TYPE.bold, True), font(TYPE.semibold), font(TYPE.medium, True))


def _label_rect(at: QPointF, font: QFont, text: str, padding: QPointF) -> QRectF:
    metrics = QFontMetricsF(font)
    return QRectF(at.x(), at.y(), metrics.horizontalAdvance(text) + 2 * padding.x(), metrics.height() + 2 * padding.y())


def _text(painter: QPainter, font: QFont, rect: QRectF, text: str, color: QColor) -> None:
    """Text centred in a pill, on the height of its capitals and digits like CenteredLabel."""
    metrics = QFontMetricsF(font)
    painter.setFont(font)
    painter.setPen(color)
    x = rect.x() + (rect.width() - metrics.horizontalAdvance(text)) / 2
    painter.drawText(QPointF(x, rect.y() + (rect.height() + metrics.capHeight()) / 2), text)
