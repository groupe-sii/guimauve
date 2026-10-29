"""View of the image of a variant: zoom, panning, the pixel under the mouse and the targets."""

import math
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
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
from guimauve.gui.element_editor_next.canvas.region import Region
from guimauve.gui.element_editor_next.canvas.region_editor import RegionEditor
from guimauve.gui.element_editor_next.canvas.target_item import TargetItem, TargetMarker
from guimauve.gui.element_editor_next.canvas.tools import REGION_TOOLS, Tool
from guimauve.gui.element_editor_next.components.magnifier import label_height, magnifier_rect, paint_magnifier
from guimauve.gui.element_editor_next.theme import METRICS, SEMANTIC, TYPE, ThemeManager

PAN_BUTTONS = (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton)
NUDGE = {Qt.Key.Key_Left: (-1, 0), Qt.Key.Key_Right: (1, 0), Qt.Key.Key_Up: (0, -1), Qt.Key.Key_Down: (0, 1)}
NUDGE_FAR = 10
"""Pixels moved by an arrow key with Shift."""
HIDE_KEY = Qt.Key.Key_H
TOOL_KEYS = {
    Qt.Key.Key_S: Tool.SELECT,
    Qt.Key.Key_T: Tool.TARGET,
    Qt.Key.Key_M: Tool.MATCH_AREA,
    Qt.Key.Key_C: Tool.CROP,
}
CONFIRM_KEYS = (Qt.Key.Key_Return, Qt.Key.Key_Enter)
MATCH_AREA_DASH = [4.0, 3.0]


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

    The Target tool, chosen with set_tool or the T key, turns a click outside the targets into a new target, inside
    the image or not, and shows a magnifier while the cursor is on the image. Esc and S go back to Select. Dragging
    a target aims like the Target tool: cross cursor, and the magnifier on the pixel it is dropped on, while that
    pixel is in the image.

    The match area, from set_match_area, is drawn dashed. The Match area (M) and Crop (C) tools edit a rectangle on
    the image, starting from the whole image unless set_region gives another; Enter confirms it, the owner of the
    view applying it, and Esc or another tool drops it. A new image drops it too. The targets stay visible but are
    not handled.

    H, or set_overlays_hidden, hides the targets and the match area to see the image alone; adding a target shows
    them again.

    Read-only, from set_read_only, the view keeps the zoom, the panning and H, but has no tool but Select and
    reports no press, drag, nudge or delete of a target.
    """

    zoom_changed = Signal()
    moved = Signal()
    """The image moved in the view: zoom, panning or resize."""
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
    """The active tool changed."""
    region_changed = Signal()
    """The rectangle edited changed, started or stopped."""
    region_confirmed = Signal()
    """Enter while a rectangle is edited."""
    overlays_changed = Signal()
    """The targets and the match area were hidden or shown."""

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
        self._read_only = False
        self._pointer: QPointF | None = None
        self._label_font = QFont(QApplication.font())
        self._label_font.setPixelSize(TYPE.caption)
        self._label_font.setWeight(QFont.Weight(TYPE.medium))
        self._label_font.setFeature(QFont.Tag("tnum"), 1)
        self._dots: tuple[tuple[str, str, float], QPixmap] | None = None
        self._match_area: Region | None = None
        self._overlays_hidden = False
        self._editor = RegionEditor(self, self._label_font)
        self._editor.changed.connect(self._region_changed)

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
        """Shows an image, or none, fitted to the view; without image, the tool goes back to Select."""
        if self._tool in REGION_TOOLS or image is None:
            self.set_tool(Tool.SELECT)  # the rectangle belonged to the image replaced
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
                item.setVisible(not self._overlays_hidden)
                self.scene().addItem(item)

    def overlays_hidden(self) -> bool:
        return self._overlays_hidden

    def set_overlays_hidden(self, hidden: bool) -> None:
        """Hides the targets and the match area, or shows them again."""
        if hidden != self._overlays_hidden:
            self._overlays_hidden = hidden
            for item in self._targets.values():
                item.setVisible(not hidden)
            self.viewport().update()
            self.overlays_changed.emit()

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
        return self._tool

    def is_read_only(self) -> bool:
        return self._read_only

    def set_read_only(self, read_only: bool) -> None:
        """Shows the image without editing it; the tool in use, and its rectangle, are dropped."""
        self._read_only = read_only
        if read_only:
            self.set_tool(Tool.SELECT)
        if self._pointer is not None and self._press is None:
            self._update_cursor(self._pointer)

    def set_tool(self, tool: Tool) -> None:
        """Chooses a tool; every tool but Select needs an image, and an editable view."""
        image = self._image
        if tool is not Tool.SELECT and (image is None or self._read_only):
            return
        if tool is not self._tool:
            self._tool = tool
            if image is not None and tool in REGION_TOOLS:
                self._editor.start(Region.whole(image.width(), image.height()))
            elif self._editor.region is not None:
                self._editor.stop()
            if self._pointer is not None and self._press is None:
                self._update_cursor(self._pointer)
            self.viewport().update()
            self.tool_changed.emit()

    # Rectangles

    def match_area(self) -> Region | None:
        return self._match_area

    def set_match_area(self, region: Region | None) -> None:
        """Match area to draw, None for the whole image."""
        if region != self._match_area:
            self._match_area = region
            self.viewport().update()

    def region(self) -> Region | None:
        """Rectangle edited, None outside the Match area and Crop tools."""
        return self._editor.region

    def set_region(self, region: Region) -> None:
        """Rectangle to edit in place of the whole image, in a tool editing one."""
        if self._tool in REGION_TOOLS:
            self._editor.start(region)

    def region_rect(self) -> QRectF | None:
        """Rectangle edited, in coordinates of the viewport."""
        return None if self._editor.region is None else self._editor.view_rect()

    def _region_changed(self) -> None:
        self.viewport().update()
        self.region_changed.emit()

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
        if button == Qt.MouseButton.LeftButton and self._editor.region is not None:
            self._editor.press(point)
            event.accept()
            return
        self._press = _Press(point, point)
        key = self.target_at(point) if button == Qt.MouseButton.LeftButton and not self._read_only else None
        if key is not None:
            marker = self._targets[key].marker
            self._press.target = key
            self._press.offset = QPointF(marker.x + 0.5, marker.y + 0.5) - self.to_image(point)
            self.target_pressed.emit(key)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        press, point = self._press, event.position()
        self._pointer = point
        if self._editor.is_dragging():
            self._editor.move(point)
            self._hover(point)
            event.accept()
            return
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
        if self._editor.is_dragging() and event.button() == Qt.MouseButton.LeftButton:
            self._editor.release()
            self._update_cursor(event.position())
            event.accept()
            return
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
                self.set_overlays_hidden(False)  # the target added must be seen
                pixel = self.to_image(event.position())
                self.target_added.emit(math.floor(pixel.x()), math.floor(pixel.y()))
            else:
                self.background_clicked.emit()
        self._update_cursor(event.position())
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        plain = not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if key == Qt.Key.Key_Escape and self._tool is not Tool.SELECT:
            self.set_tool(Tool.SELECT)
        elif key in CONFIRM_KEYS and self._editor.region is not None:
            self.region_confirmed.emit()
        elif key == HIDE_KEY and plain:
            self.set_overlays_hidden(not self._overlays_hidden)
        elif self._read_only:
            super().keyPressEvent(event)
            return
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
        if self._match_area is not None and self._tool is not Tool.MATCH_AREA and not self._overlays_hidden:
            match = self._match_area
            pen = QPen(QColor(SEMANTIC.area), 1.5)
            pen.setDashPattern([length / 1.5 for length in MATCH_AREA_DASH])  # in units of the pen width
            painter.setPen(pen)
            painter.drawRect(self.viewportTransform().mapRect(QRectF(match.left, match.top, match.width, match.height)))
        self._editor.paint(painter)
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
        self.moved.emit()
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
        if self._editor.region is not None:
            self.viewport().setCursor(self._editor.cursor_at(point))
        elif not self._read_only and self.target_at(point) is not None:
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
