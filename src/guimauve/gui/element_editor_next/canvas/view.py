"""View of the image of a variant: zoom, panning and the pixel under the mouse."""

import math

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QImage,
    QMouseEvent,
    QNativeGestureEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
    QShowEvent,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget

from guimauve.gui.element_editor_next.canvas import zoom as zooms
from guimauve.gui.element_editor_next.theme import METRICS, SEMANTIC, ThemeManager

PAN_BUTTONS = (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton)


class CanvasView(QGraphicsView):
    """Image on a dotted background, framed by a thin line; scene coordinates are pixels of the image.

    The zoom counts physical pixels of the screen per pixel of the image (see canvas.zoom). The image fits the view
    when set, and keeps fitting as the view is resized until the user zooms or pans. The wheel and a pinch zoom on
    the cursor; dragging with the left button on the image or the background, or with the middle button anywhere,
    moves the view. Beyond 100 %, the pixels are drawn without smoothing.
    """

    zoom_changed = Signal()
    hovered_changed = Signal()
    """The pixel under the mouse changed, or the mouse left the image."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self._image: QImage | None = None
        self._zoom = 1.0
        self._fitting = True
        self._center = QPointF()
        self._hovered: QPoint | None = None
        self._pan_from: QPointF | None = None
        self._dots: tuple[tuple[str, str, float], QPixmap] | None = None

        self._item = QGraphicsPixmapItem()
        self._item.setVisible(False)
        scene = QGraphicsScene(self)
        scene.addItem(self._item)
        self.setScene(scene)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)  # the dots stay in place
        self.viewport().setMouseTracking(True)
        theme.changed.connect(self.viewport().update)

    # Image and zoom

    def image(self) -> QImage | None:
        return self._image

    def set_image(self, image: QImage | None) -> None:
        """Shows an image, or none, fitted to the view."""
        self._image = image
        self._item.setPixmap(QPixmap() if image is None else QPixmap.fromImage(image))
        self._item.setVisible(image is not None)
        self.fit()
        self._hover(self._cursor())

    @property
    def zoom(self) -> float:
        return self._zoom

    def is_fitting(self) -> bool:
        return self._fitting

    def fit(self) -> None:
        """Fits the whole image in the view, enlarged at most twice, and keeps fitting it when the view is resized."""
        self._fitting = True
        if self._image is None:
            self._set(1.0, QPointF())
            return
        ratio, margin = self.devicePixelRatioF(), 2 * METRICS.canvas_margin
        width = (self.viewport().width() - margin) * ratio
        height = (self.viewport().height() - margin) * ratio
        self._set(zooms.fit(self._image.width(), self._image.height(), width, height), self._image_rect().center())

    def set_zoom(self, zoom: float, anchor: QPointF | None = None) -> None:
        """Zooms, keeping the pixel under anchor, a point of the viewport, in place; the centre by default.

        Does nothing without image.
        """
        if self._image is None:
            return
        self._fitting = False
        zoom = zooms.clamp(zoom)
        center = self._center
        if anchor is not None:
            offset = anchor - QRectF(self.viewport().rect()).center()
            center = self.to_image(anchor) - _divided(offset, zoom / self.devicePixelRatioF())
        self._set(zoom, center)

    def zoom_in(self) -> None:
        self.set_zoom(zooms.zoom_in(self._zoom))

    def zoom_out(self) -> None:
        self.set_zoom(zooms.zoom_out(self._zoom))

    def to_image(self, point: QPointF) -> QPointF:
        """Point of the viewport in coordinates of the image."""
        inverse, _ = self.viewportTransform().inverted()
        return inverse.map(point)

    # Pixel under the mouse

    def hovered_pixel(self) -> QPoint | None:
        return self._hovered

    def hovered_color(self) -> QColor | None:
        if self._hovered is None or self._image is None:
            return None
        return self._image.pixelColor(self._hovered)

    # Events

    def wheelEvent(self, event: QWheelEvent) -> None:
        notches = event.angleDelta().y() / 120
        if notches:
            self.set_zoom(zooms.wheel(self._zoom, notches), event.position())
        event.accept()

    def viewportEvent(self, event: QEvent) -> bool:
        if isinstance(event, QNativeGestureEvent) and event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
            self.set_zoom(self._zoom * (1 + event.value()), event.position())
            return True
        if event.type() == QEvent.Type.Leave:
            self._hover(None)
        return super().viewportEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() in PAN_BUTTONS and self._image is not None:
            self._pan_from = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_from is not None:
            delta = event.position() - self._pan_from
            self._pan_from = event.position()
            self._fitting = False
            self._set(self._zoom, self._center - _divided(delta, self._scale()))
        self._hover(event.position())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._pan_from is not None and event.button() in PAN_BUTTONS:
            self._pan_from = None
            self.viewport().unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh()

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._refresh()

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.DevicePixelRatioChange:  # moved to a screen with another scaling
            self._refresh()
        return super().event(event)

    # Painting

    def drawBackground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        painter.save()
        painter.resetTransform()
        palette = self._theme.palette
        area = self.viewport().rect()
        painter.fillRect(area, QBrush(self._dot_tile(palette.canvas, palette.canvas_dot)))
        painter.restore()

    def drawForeground(self, painter: QPainter, rect: QRectF | QRect) -> None:
        if self._image is None:
            return
        painter.save()
        frame = self.viewportTransform().mapRect(self._image_rect())
        painter.resetTransform()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(SEMANTIC.image_border), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(frame.adjusted(-0.5, -0.5, 0.5, 0.5))  # just outside the image, which stays whole
        painter.restore()

    # Internals

    def _scale(self) -> float:
        """Logical pixels of the viewport per pixel of the image."""
        return self._zoom / self.devicePixelRatioF()

    def _image_rect(self) -> QRectF:
        return QRectF(0, 0, 0, 0) if self._image is None else QRectF(self._image.rect())

    def _refresh(self) -> None:
        if self._fitting:
            self.fit()
        else:
            self._set(self._zoom, self._center)

    def _set(self, zoom: float, center: QPointF) -> None:
        """Applies a zoom and the point of the image at the centre of the view, kept on the image."""
        changed = zoom != self._zoom
        self._zoom = zoom
        bounds = self._image_rect()
        self._center = QPointF(
            min(max(center.x(), bounds.left()), bounds.right()), min(max(center.y(), bounds.top()), bounds.bottom())
        )
        scale = self._scale()
        self.setTransform(QTransform.fromScale(scale, scale))
        reach = max(self.viewport().width(), self.viewport().height()) / scale  # room to centre any point
        self.setSceneRect(bounds.adjusted(-reach, -reach, reach, reach))
        self.centerOn(self._center)
        smooth = Qt.TransformationMode.SmoothTransformation if zoom < 1 else Qt.TransformationMode.FastTransformation
        self._item.setTransformationMode(smooth)
        self.viewport().update()
        if changed:
            self.zoom_changed.emit()

    def _cursor(self) -> QPointF | None:
        if not self.viewport().underMouse():
            return None
        return QPointF(self.viewport().mapFromGlobal(QCursor.pos()))

    def _hover(self, point: QPointF | None) -> None:
        pixel = None
        if point is not None and self._image is not None:
            position = self.to_image(point)
            x, y = math.floor(position.x()), math.floor(position.y())
            if self._image.rect().contains(x, y):
                pixel = QPoint(x, y)
        if pixel != self._hovered:
            self._hovered = pixel
            self.hovered_changed.emit()

    def _dot_tile(self, background: str, dot: str) -> QPixmap:
        """One cell of the dotted background, a dot at its centre, drawn at the pixel ratio of the screen."""
        ratio = self.devicePixelRatioF()
        key = (background, dot, ratio)
        if self._dots is None or self._dots[0] != key:
            size = METRICS.canvas_grid
            tile = QPixmap(round(size * ratio), round(size * ratio))
            tile.setDevicePixelRatio(ratio)
            tile.fill(QColor(background))
            painter = QPainter(tile)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(dot))
            painter.drawEllipse(QPointF(size / 2, size / 2), 1, 1)
            painter.end()
            self._dots = (key, tile)
        return self._dots[1]


def _divided(point: QPointF, factor: float) -> QPointF:
    """Point divided by a number; the stubs of some PySide6 versions lack QPointF / float."""
    return QPointF(point.x() / factor, point.y() / factor)
