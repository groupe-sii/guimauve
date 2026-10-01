"""Low-level QGraphicsView building blocks.

:class:`CaptureView` owns a scene with a pixmap and a placeholder text
item. It does NOT own any overlay — canvases stack overlays over the
view themselves, so views stay reusable.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QWidget,
)


class ScreenView(QGraphicsView):
    """A QGraphicsView that keeps its scene fully visible on resize."""

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Re-fit the scene inside the new widget size.

        :param event: The Qt resize event.
        """
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class CaptureView(ScreenView):
    """A ScreenView specialised for showing a live screen capture.

    Owns its own scene, a pixmap item that holds the current frame,
    and a placeholder text item shown until a frame is available.
    """

    def __init__(
        self,
        width: int,
        height: int,
        placeholder_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """
        :param width: Scene width in scene units, usually the captured
            screen's physical pixel width.
        :param height: Scene height in scene units.
        :param placeholder_text: Text shown centered in the scene until
            a real frame is displayed. Empty by default.
        :param parent: Optional Qt parent widget.
        """
        scene = QGraphicsScene()
        scene.setSceneRect(0, 0, width, height)
        super().__init__(scene, parent)
        self._scene = scene

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._pixmap_item = QGraphicsPixmapItem()
        scene.addItem(self._pixmap_item)

        self._placeholder = QGraphicsTextItem(placeholder_text)
        self._placeholder.setDefaultTextColor(Qt.GlobalColor.black)
        scene.addItem(self._placeholder)
        self._center_placeholder(width, height)

    def _center_placeholder(self, width: int, height: int) -> None:
        """Center the placeholder text item inside the scene.

        :param width: Scene width in scene units.
        :param height: Scene height in scene units.
        """
        rect = self._placeholder.boundingRect()
        self._placeholder.setPos(
            (width - rect.width()) / 2,
            (height - rect.height()) / 2,
        )

    def show_frame(self, pixmap: QPixmap) -> None:
        """Display a captured frame and hide the placeholder text.

        :param pixmap: The frame to display, at scene resolution.
        """
        self._pixmap_item.setPixmap(pixmap)
        self._placeholder.setVisible(False)

    def show_placeholder(self) -> None:
        """Clear the current frame and show the placeholder text again."""
        self._pixmap_item.setPixmap(QPixmap())
        self._placeholder.setVisible(True)
