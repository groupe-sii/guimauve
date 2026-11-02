from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject


class TargetPointItem(QGraphicsObject):
    position_changed = Signal(object)
    hover_changed = Signal(object, bool)

    def __init__(self, target):
        super().__init__()
        self.target = target
        self.setPos(QPointF(self.target.x, self.target.y))

        self.setFlags(
            QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.is_hovered = False

        self._init_signals()

    def boundingRect(self):
        return QRectF(-10, -10, 20, 20)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        path_color = Qt.white if self.is_hovered else Qt.red

        painter.setPen(QPen(Qt.black, 4))
        self._draw_cross(painter, 8)

        painter.setPen(QPen(path_color, 2))
        self._draw_cross(painter, 8)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.hover_changed.emit(self.target, True)
        self.update()
        self.setCursor(Qt.OpenHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.hover_changed.emit(self.target, False)
        self.update()
        self.setCursor(Qt.CrossCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.BlankCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def _draw_cross(self, painter, size):
        painter.drawLine(-size, 0, size, 0)
        painter.drawLine(0, -size, 0, size)

    def _on_moved(self, *args):
        self.target.x = int(self.pos().x())
        self.target.y = int(self.pos().y())

        self.position_changed.emit(self.target)

    def _init_signals(self):
        self.xChanged.connect(self._on_moved)
        self.yChanged.connect(self._on_moved)
