from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem


class RectSignals(QObject):
    changed = Signal(QRectF)


class HandleItem(QGraphicsEllipseItem):
    def __init__(self, name, parent):
        super().__init__(-7, -7, 14, 14, parent)
        self.name = name
        self.setZValue(1000)
        self.setBrush(Qt.white)
        self.setPen(QPen(Qt.black, 1))

        self.setFlags(
            QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemSendsGeometryChanges
            | QGraphicsItem.ItemIgnoresTransformations
        )

        cursors = {
            "top_left": Qt.SizeFDiagCursor,
            "top_right": Qt.SizeBDiagCursor,
            "bottom_left": Qt.SizeBDiagCursor,
            "bottom_right": Qt.SizeFDiagCursor,
        }
        self.setCursor(cursors.get(name, Qt.ArrowCursor))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.parentItem():
            new_pos = self.parentItem().validate_handle_pos(self.name, value)
            self.parentItem().handle_moved(self.name, new_pos)
            return new_pos
        return super().itemChange(change, value)


class EditableRectItem(QGraphicsRectItem):
    def __init__(self, rect, pen, bounds=None):
        super().__init__(rect)
        self.bounds = bounds
        self.signals = RectSignals()
        self._is_updating = False

        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)

        self.setCursor(Qt.SizeAllCursor)
        self.setPen(pen)

        self.handles = {
            "top_left": HandleItem("top_left", self),
            "top_right": HandleItem("top_right", self),
            "bottom_left": HandleItem("bottom_left", self),
            "bottom_right": HandleItem("bottom_right", self),
        }
        self.update_handles_positions()

    def validate_handle_pos(self, name, local_pos):
        if not self.bounds:
            return local_pos

        scene_pos = self.mapToScene(local_pos)
        sx = max(self.bounds.left(), min(scene_pos.x(), self.bounds.right()))
        sy = max(self.bounds.top(), min(scene_pos.y(), self.bounds.bottom()))
        return self.mapFromScene(QPointF(sx, sy))

    def handle_moved(self, name, pos):
        if self._is_updating:
            return

        r = self.rect()
        if name == "top_left":
            r.setTopLeft(pos)
        elif name == "top_right":
            r.setTopRight(pos)
        elif name == "bottom_left":
            r.setBottomLeft(pos)
        elif name == "bottom_right":
            r.setBottomRight(pos)

        self.setRect(r.normalized())
        self.update_handles_positions(exclude=name)
        self._emit_change()

    def update_handles_positions(self, exclude=None):
        self._is_updating = True
        r = self.rect()
        mapping = {
            "top_left": r.topLeft(),
            "top_right": r.topRight(),
            "bottom_left": r.bottomLeft(),
            "bottom_right": r.bottomRight(),
        }
        for name, pos in mapping.items():
            if name != exclude:
                self.handles[name].setPos(pos)
        self._is_updating = False

    def set_editable(self, editable):
        self.setFlag(QGraphicsItem.ItemIsSelectable, editable)
        self.setCursor(Qt.SizeAllCursor if editable else Qt.CrossCursor)

        for handle in self.handles.values():
            handle.setVisible(editable)
        self.update()

    def mousePressEvent(self, event):
        for handle in self.handles.values():
            if handle.isVisible() and handle.contains(handle.mapFromParent(event.pos())):
                event.setAccepted(False)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.isSelected() and self.handles["top_left"].isVisible():
            delta = event.pos() - event.lastPos()
            new_rect = self.rect().translated(delta)

            if self.bounds:
                if new_rect.left() < self.bounds.left():
                    new_rect.moveLeft(self.bounds.left())
                if new_rect.right() > self.bounds.right():
                    new_rect.moveRight(self.bounds.right())
                if new_rect.top() < self.bounds.top():
                    new_rect.moveTop(self.bounds.top())
                if new_rect.bottom() > self.bounds.bottom():
                    new_rect.moveBottom(self.bounds.bottom())

            self.setRect(new_rect)
            self.update_handles_positions()
            self._emit_change()
            return

        super().mouseMoveEvent(event)

    def paint(self, painter, option, widget):
        if self.bounds and self.handles["top_left"].isVisible():
            painter.save()
            r = self.rect()
            b = self.mapFromScene(self.bounds).boundingRect()

            painter.setBrush(QColor(0, 0, 0, 160))
            painter.setPen(Qt.NoPen)

            painter.drawRect(QRectF(b.left(), b.top(), b.width(), r.top() - b.top()))
            painter.drawRect(QRectF(b.left(), r.bottom(), b.width(), b.bottom() - r.bottom()))
            painter.drawRect(QRectF(b.left(), r.top(), r.left() - b.left(), r.height()))
            painter.drawRect(QRectF(r.right(), r.top(), b.right() - r.right(), r.height()))
            painter.restore()

        super().paint(painter, option, widget)

    def _emit_change(self):
        self.signals.changed.emit(self.rect())
