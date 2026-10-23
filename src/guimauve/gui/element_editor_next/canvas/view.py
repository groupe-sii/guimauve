"""View of the image of a variant: zoom, panning, the pixel under the mouse and the targets."""

import math
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFocusEvent,
    QFont,
    QImage,
    QKeyEvent,
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
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget

from guimauve.gui.element_editor_next.canvas import zoom as zooms
from guimauve.gui.element_editor_next.canvas.target_item import TargetItem, TargetMarker
from guimauve.gui.element_editor_next.canvas.tools import Tool
from guimauve.gui.element_editor_next.components.magnifier import label_height, magnifier_rect, paint_magnifier
from guimauve.gui.element_editor_next.theme import METRICS, SEMANTIC, TYPE, ThemeManager

PAN_BUTTONS = (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton)
NUDGE = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
NUDGE_FAR = 10
"""Pixels moved by an arrow key with Shift."""
TOOL_KEYS = {Qt.Key.Key_V: Tool.SELECT, Qt.Key.Key_T: Tool.TARGET}


@dataclass
class _Press:
    """A press of the left or middle button, until released: a click, a drag of a target or of the view."""

    start: QPointF
    last: QPointF
    target: int | None = None
    offset: QPointF | None = None  # from the pointer to the centre of the pixel of the target, in image pixels
    moved: bool = False


class CanvasView(QGraphicsView):
    """Image on a dotted background, framed by a thin line; scene coordinates are pixels of the image.

    The zoom counts physical pixels of the screen per pixel of the image (see canvas.zoom). The image fits the view
    when set, and keeps fitting as the view is resized until the user zooms or pans. The wheel and a pinch zoom on
    the cursor; dragging with the left button on the image or the background, or with the middle button anywhere,
    moves the view. Beyond 100 %, the pixels are drawn without smoothing.

    The targets come from set_targets. The view does not change them: it reports a press on a target, its drag
    pixel by pixel and its release, a click on the background, and the arrow and delete keys while it has the focus.

    The Target tool, chosen with set_tool or the T key, or held with Ctrl over the Select tool, turns a click outside
    the targets into a new target, inside the image or not, and shows a magnifier while the cursor is on the image.
    Esc and V go back to Select. Dragging a target aims like the Target tool: cross cursor, and the magnifier on the
    pixel it is dropped on, while that pixel is in the image.
    """

    zoom_changed = Signal()
    hovered_changed = Signal()
    """The pixel under the mouse changed, or the mouse left the image."""
    target_pressed = Signal(int)
    target_dragged = Signal(int, int, int)
    """Key of the target and the pixel it is dragged to, inside the image or not."""
    target_released = Signal(int)
    background_clicked = Signal()
    """A click without drag outside the targets."""
    nudge_requested = Signal(int, int)
    delete_requested = Signal()
    target_added = Signal(int, int)
    """A click in the Target tool, at this pixel."""
    tool_changed = Signal()
    """The active tool changed, chosen or held with Ctrl."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self._image: QImage | None = None
        self._zoom = 1.0
        self._fitting = True
        self._center = QPointF()
        self._hovered: QPoint | None = None
        self._press: _Press | None = None
        self._targets: dict[int, TargetItem] = {}
        self._tool = Tool.SELECT
        self._ctrl = False
        self._ctrl_zooms = False
        self._pointer: QPointF | None = None
        self._label_font = QFont(QApplication.font())
        self._label_font.setPixelSize(TYPE.caption)
        self._label_font.setWeight(QFont.Weight(TYPE.medium))
        self._label_font.setFeature(QFont.Tag("tnum"), 1)
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
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
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

    # Targets

    def set_targets(self, markers: list[TargetMarker]) -> None:
        """Shows these targets, adding, updating or removing crosshairs by key."""
        wanted = {marker.key: marker for marker in markers}
        for key in [key for key in self._targets if key not in wanted]:
            self.scene().removeItem(self._targets.pop(key))
        for key, marker in wanted.items():
            if key in self._targets:
                if self._targets[key].marker != marker:
                    self._targets[key].set_marker(marker)
            else:
                self._targets[key] = item = TargetItem(marker)
                self.scene().addItem(item)

    def target_items(self) -> list[TargetItem]:
        return list(self._targets.values())

    def target_at(self, point: QPointF) -> int | None:
        """Key of the target under a point of the viewport, the one drawn on top first."""
        for item in self.items(point.toPoint()):
            if isinstance(item, TargetItem):
                return item.marker.key
        return None

    # Tools

    @property
    def tool(self) -> Tool:
        """Active tool: the one chosen, or Target while Ctrl is held over Select."""
        if self._tool is Tool.SELECT and self._ctrl:
            return Tool.TARGET
        return self._tool

    def set_tool(self, tool: Tool) -> None:
        self._change_tool(lambda: setattr(self, "_tool", tool))

    def _hold_ctrl(self, held: bool) -> None:
        """Ctrl pressed or released; while it zooms with the wheel, it does not hold the Target tool."""
        if not held:
            self._ctrl_zooms = False
        elif self._ctrl_zooms:
            return
        self._change_tool(lambda: setattr(self, "_ctrl", held))

    def _change_tool(self, change) -> None:
        before = self.tool
        change()
        if self.tool is not before:
            if self._pointer is not None and self._press is None:
                self._update_cursor(self._pointer)
            self.viewport().update()
            self.tool_changed.emit()

    # Pixel under the mouse

    def hovered_pixel(self) -> QPoint | None:
        return self._hovered

    def hovered_color(self) -> QColor | None:
        if self._hovered is None or self._image is None:
            return None
        return self._image.pixelColor(self._hovered)

    # Events

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # A pinch on a Windows touchpad arrives as Ctrl and the wheel: Ctrl then zooms, it is not held
            self._hold_ctrl(False)
            self._ctrl_zooms = True
        notches = event.angleDelta().y() / 120
        if notches:
            self.set_zoom(zooms.wheel(self._zoom, notches), event.position())
        event.accept()

    def viewportEvent(self, event: QEvent) -> bool:
        if isinstance(event, QNativeGestureEvent) and event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
            self.set_zoom(self._zoom * (1 + event.value()), event.position())
            return True
        if event.type() == QEvent.Type.Leave:
            self._pointer = None
            self._hover(None)
            self.viewport().update()
        return super().viewportEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        button, point = event.button(), event.position()
        if button not in PAN_BUTTONS or self._press is not None:
            super().mousePressEvent(event)
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self._hold_ctrl(bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
        self._press = _Press(point, point)
        key = self.target_at(point) if button == Qt.MouseButton.LeftButton else None
        if key is not None:
            marker = self._targets[key].marker
            self._press.target = key
            self._press.offset = QPointF(marker.x + 0.5, marker.y + 0.5) - self.to_image(point)
            self.target_pressed.emit(key)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        press, point = self._press, event.position()
        self._pointer = point
        self._hold_ctrl(bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
        if press is not None:
            if not press.moved and (point - press.start).manhattanLength() >= QApplication.startDragDistance():
                press.moved = True
                dragging = press.target is not None
                cursor = Qt.CursorShape.CrossCursor if dragging else Qt.CursorShape.ClosedHandCursor
                self.viewport().setCursor(cursor)
            if press.moved:
                self._drag(press, point)
            press.last = point
        else:
            self._update_cursor(point)
        self._hover(point)
        if self.tool is Tool.TARGET or (press is not None and press.target is not None):
            self.viewport().update()  # the magnifier follows the cursor
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        press = self._press
        if press is None or event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.MiddleButton):
            super().mouseReleaseEvent(event)
            return
        self._press = None
        self.viewport().unsetCursor()
        if press.target is not None:
            self.target_released.emit(press.target)
        elif not press.moved and event.button() == Qt.MouseButton.LeftButton:
            if self.tool is Tool.TARGET:
                pixel = self.to_image(event.position())
                self.target_added.emit(math.floor(pixel.x()), math.floor(pixel.y()))
            else:
                self.background_clicked.emit()
        self._update_cursor(event.position())
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        plain = not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if key == Qt.Key.Key_Control:
            self._hold_ctrl(True)
            super().keyPressEvent(event)
            return
        if key == Qt.Key.Key_Escape and self._tool is not Tool.SELECT:
            self.set_tool(Tool.SELECT)
        elif key in TOOL_KEYS and plain:
            self.set_tool(TOOL_KEYS[Qt.Key(key)])
        elif key in NUDGE:
            step = NUDGE_FAR if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx, dy = NUDGE[Qt.Key(key)]
            self.nudge_requested.emit(dx * step, dy * step)
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Control:
            self._hold_ctrl(False)
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._hold_ctrl(False)
        super().focusOutEvent(event)

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
        aimed = self.aimed_pixel()
        if aimed is not None and self._pointer is not None:
            area = QRectF(self.viewport().rect())
            where = magnifier_rect(self._pointer, area, label_height(self._label_font))
            outside = QColor(self._theme.palette.canvas)
            paint_magnifier(painter, self._image, aimed, where, outside, self._label_font)
        painter.restore()

    def shows_magnifier(self) -> bool:
        return self.aimed_pixel() is not None

    def aimed_pixel(self) -> QPoint | None:
        """Pixel of the image under the magnifier: where a dragged target drops, or under the cursor in the Target
        tool when the view is not being moved; None outside the image."""
        press, pixel = self._press, None
        if self._image is None or self._pointer is None:
            return None
        if press is not None and press.moved:
            if press.target is not None and press.offset is not None:
                centre = self.to_image(self._pointer) + press.offset
                pixel = QPoint(math.floor(centre.x()), math.floor(centre.y()))
        elif self.tool is Tool.TARGET:
            pixel = self._hovered
        return pixel if pixel is not None and self._image.rect().contains(pixel) else None

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

    def _drag(self, press: _Press, point: QPointF) -> None:
        """Moves the target pressed to the pixel under the pointer, or the view by the move of the pointer."""
        if press.target is not None and press.offset is not None:
            centre = self.to_image(point) + press.offset
            self.target_dragged.emit(press.target, math.floor(centre.x()), math.floor(centre.y()))
        elif self._image is not None:
            self._fitting = False
            self._set(self._zoom, self._center - _divided(point - press.last, self._scale()))

    def _update_cursor(self, point: QPointF) -> None:
        if self.target_at(point) is not None:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        elif self.tool is Tool.TARGET:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.viewport().unsetCursor()

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
