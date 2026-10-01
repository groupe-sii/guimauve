"""The main canvas: the big preview of the captured desktop.

Wraps a :class:`CaptureView` in an aspect-ratio container and stacks
the keyboard overlay on top of the view. This canvas is what the main
window plugs the :class:`PreviewPlayer` into.
"""

from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import QGraphicsScene, QWidget

from guimauve.gui.replay_editor.widgets.aspect_ratio_container import AspectRatioContainer
from guimauve.gui.replay_editor.widgets.keyboard_overlay import KeyboardOverlay
from guimauve.gui.replay_editor.widgets.screen_view import CaptureView


class ScreenCanvas(AspectRatioContainer):
    """Aspect-ratio-locked view of the captured screen, with a keyboard overlay."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        parent: QWidget | None = None,
    ) -> None:
        """
        :param screen_width: Captured screen width in physical pixels.
        :param screen_height: Captured screen height in physical pixels.
        :param parent: Optional Qt parent widget.
        """
        ratio = screen_height / screen_width
        view = CaptureView(screen_width, screen_height, "")
        view.setStyleSheet("background-color: White; border: 2px dashed black;")
        super().__init__(view, ratio, parent)
        self._overlay = KeyboardOverlay(view)

    def show_frame(self, pixmap: QPixmap) -> None:
        """Display a captured frame on the canvas.

        :param pixmap: The frame to display, at scene resolution.
        """
        self.child.show_frame(pixmap)

    def show_placeholder(self) -> None:
        """Clear the current frame and show the placeholder text again."""
        self.child.show_placeholder()

    def scene(self) -> QGraphicsScene:
        """:return: The underlying QGraphicsScene the preview draws on."""
        return self.child.scene()

    def overlay(self) -> KeyboardOverlay:
        """:return: The keyboard overlay stacked over the canvas."""
        return self._overlay

    def resizeEvent(self, event: QResizeEvent | None) -> None:
        """Reposition the overlay after the container has been resized.

        :param event: The Qt resize event, or ``None`` when called
            manually.
        """
        super().resizeEvent(event)
        self._overlay.reposition()
