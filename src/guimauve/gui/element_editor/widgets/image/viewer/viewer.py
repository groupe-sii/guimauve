from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen, QTransform
from PySide6.QtWidgets import QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from guimauve.gui.element_editor.widgets.image.viewer.editable_rect import EditableRectItem


class ImageViewer(QGraphicsView):
    ZOOM_STEPS = [
        0.1,
        0.15,
        0.2,
        0.25,
        0.35,
        0.5,
        0.65,
        0.8,
        0.9,
        1.0,  # 100%
        1.1,
        1.25,
        1.5,
        2.0,
        3.0,
        4.0,
        5.0,
        6.0,
        8.0,
        10.0,
    ]

    view_changed = Signal(float)
    mouse_moved = Signal(QPointF)
    point_clicked = Signal(QPointF)
    crop_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))

        self.pixmap_item = None
        self.crop_item = None
        self.match_area_item = None
        self.block_targets = False

        self.neutral_scale = 1.0 / self.screen().devicePixelRatio()
        self.current_zoom_step = self.ZOOM_STEPS.index(1.0)
        self.set_zoom_level(1.0)

        self.viewport().setCursor(Qt.CrossCursor)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.StrongFocus)

        self._init_signals()

    @property
    def has_image(self):
        return self.pixmap_item is not None

    @property
    def is_in_crop_mode(self):
        return self.crop_item is not None

    @property
    def zoom_level(self):
        return self.transform().m11() / self.neutral_scale

    def set_zoom_level(self, user_value):
        physical_value = user_value * self.neutral_scale

        transform = QTransform()
        transform.scale(physical_value, physical_value)
        self.setTransform(transform)

        self.sync_zoom_index()
        self.view_changed.emit(user_value)

    def sync_zoom_index(self):
        self.current_zoom_step = min(
            range(len(self.ZOOM_STEPS)), key=lambda i: abs(self.ZOOM_STEPS[i] - self.zoom_level)
        )

    def set_image(self, pixmap):
        self.remove_image()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setZValue(-1)
        self.scene().addItem(self.pixmap_item)
        self.scene().setSceneRect(self.pixmap_item.boundingRect())
        self.fit_image()

    def remove_image(self):
        if self.has_image:
            self.scene().removeItem(self.pixmap_item)
        self.pixmap_item = None

        self.scene().setSceneRect(QRectF())

    def fit_image(self):
        if not self.has_image:
            return

        image_rect = self.scene().sceneRect()
        view_size = self.viewport().size()

        if view_size.width() <= 50 or view_size.height() <= 50:
            self.set_zoom_level(1.0)
            self.centerOn(self.pixmap_item)
            return

        if image_rect.width() <= view_size.width() and image_rect.height() <= view_size.height():
            target_zoom = 1.0
        else:
            ratio_w = view_size.width() / image_rect.width()
            ratio_h = view_size.height() / image_rect.height()
            ideal_fit = min(ratio_w, ratio_h) * 0.95

            possible_steps = [s for s in self.ZOOM_STEPS if s <= ideal_fit]
            target_zoom = max(possible_steps) if possible_steps else self.ZOOM_STEPS[0]

        self.set_zoom_level(target_zoom)
        self.centerOn(self.pixmap_item)

    def set_crop_visible(self, visible):
        if not self.has_image:
            return

        if visible:
            if not self.is_in_crop_mode:
                img_rect = self.pixmap_item.boundingRect()
                self.crop_item = EditableRectItem(img_rect, QPen(Qt.white, 1, Qt.DashLine), bounds=img_rect)
                self.crop_item.signals.changed.connect(self.crop_changed)
                self.scene().addItem(self.crop_item)
            self.crop_item.show()
        else:
            if self.is_in_crop_mode:
                self.scene().removeItem(self.crop_item)
            self.crop_item = None
            self.scene().update()

    def get_crop_rect(self):
        if not self.is_in_crop_mode:
            return None

        scene_rect = self.crop_item.mapToScene(self.crop_item.rect()).boundingRect()
        return self.mapFromScene(scene_rect).boundingRect()

    def apply_crop(self):
        if not self.is_in_crop_mode or not self.has_image:
            return None

        scene_rect = self.crop_item.mapToScene(self.crop_item.rect()).boundingRect()

        image_rect = self.pixmap_item.boundingRect()
        final_rect = scene_rect.intersected(image_rect).toAlignedRect()

        original_pixmap = self.pixmap_item.pixmap()
        cropped_pixmap = original_pixmap.copy(final_rect)

        self.set_image(cropped_pixmap)
        return cropped_pixmap

    def set_match_area_visible(self, visible, rect=None):
        if not self.has_image:
            return

        if not visible:
            if self.match_area_item:
                self.match_area_item.set_editable(False)
                self.match_area_item.hide()
            return

        if self.match_area_item:
            self.match_area_item.set_editable(True)
            self.match_area_item.show()
            return

        is_new = rect is None

        if is_new:
            img_rect = self.pixmap_item.boundingRect()
            rect = QRectF(0, 0, img_rect.width() * 0.5, img_rect.height() * 0.5)
            rect.moveCenter(img_rect.center())

        pen = QPen(QColor(255, 0, 0), 2, Qt.SolidLine)
        self.match_area_item = EditableRectItem(rect, pen, bounds=self.pixmap_item.boundingRect())
        self.match_area_item.signals.changed.connect(self.crop_changed)
        self.scene().addItem(self.match_area_item)

        self.match_area_item.set_editable(is_new)
        self.match_area_item.show()

    def get_match_area_rect(self):
        if not self.match_area_item:
            return None
        return self.match_area_item.rect()

    def remove_match_area(self):
        if self.match_area_item:
            self.scene().removeItem(self.match_area_item)
            self.match_area_item = None

    def wheelEvent(self, event):
        modifiers = event.modifiers()
        delta = event.angleDelta()

        # CTRL + Scroll = Zoom
        if modifiers == Qt.ControlModifier:
            if delta.y() > 0:
                if self.current_zoom_step < len(self.ZOOM_STEPS) - 1:
                    self.current_zoom_step += 1
            else:
                if self.current_zoom_step > 0:
                    self.current_zoom_step -= 1

            self.set_zoom_level(self.ZOOM_STEPS[self.current_zoom_step])
            event.accept()
            return

        # SHIFT + Scroll = Horizontal scroll
        if modifiers == Qt.ShiftModifier:
            h_delta = delta.y()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - h_delta)
            event.accept()
            return

        super().wheelEvent(event)

    def mousePressEvent(self, event):
        # Point creation
        if not self.block_targets and event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier:
            scene_pos = self.mapToScene(event.pos())
            self.point_clicked.emit(scene_pos)
            event.accept()
            return

        # Panning
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake_event = QMouseEvent(event.type(), event.position(), Qt.LeftButton, Qt.LeftButton, event.modifiers())
            super().mousePressEvent(fake_event)
            return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Panning
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(Qt.CrossCursor)

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        self.mouse_moved.emit(scene_pos)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.mouse_moved.emit(QPointF(float("nan"), float("nan")))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._emit_view_changed()

    def showEvent(self, event):
        super().showEvent(event)
        if self.has_image:
            self.fit_image()

    def _emit_view_changed(self):
        self.view_changed.emit(self.zoom_level)

    def _init_signals(self):
        self.horizontalScrollBar().valueChanged.connect(lambda _: self._emit_view_changed())
        self.verticalScrollBar().valueChanged.connect(lambda _: self._emit_view_changed())
