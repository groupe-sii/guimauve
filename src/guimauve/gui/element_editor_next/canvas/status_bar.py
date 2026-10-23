"""Bar under the canvas: the pixel under the mouse, its color and the size of the image."""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from guimauve.gui.element_editor_next.theme import METRICS

SWATCH = 10
NONE = "–"


def tabular(widget: QWidget) -> None:
    """Digits of the same width, so numbers do not shift as they change."""
    font = widget.font()
    font.setFeature(QFont.Tag("tnum"), 1)
    widget.setFont(font)


class CanvasStatusBar(QFrame):
    """Position and color of the pixel under the mouse, or a dash outside the image, then the size of the image.

    Empty when there is no image.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("canvasStatus")
        self.setFixedHeight(METRICS.canvas_status_height)
        self.position = QLabel()
        self._swatch = QFrame()
        self._swatch.setFixedSize(SWATCH, SWATCH)
        self.color = QLabel()
        self.size_label = QLabel()
        for label in (self.position, self.color, self.size_label):
            tabular(label)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(3), 0, METRICS.space(3), 0)
        layout.setSpacing(METRICS.space(4))
        layout.addWidget(self.position)
        color = QHBoxLayout()
        color.setSpacing(METRICS.space(1) + 2)
        color.addWidget(self._swatch, 0, Qt.AlignmentFlag.AlignVCenter)
        color.addWidget(self.color)
        layout.addLayout(color)
        layout.addWidget(self.size_label)
        layout.addStretch()
        self.show_pixel(None, None, None)

    def show_pixel(self, size: tuple[int, int] | None, pixel: QPoint | None, color: QColor | None) -> None:
        """Shows the image of this size, or none, and the pixel under the mouse with its color, or none."""
        self.position.setText(NONE if pixel is None else f"x {pixel.x()}, y {pixel.y()}")
        self.position.setVisible(size is not None)
        hex_color = None if color is None else color.name().upper()
        self.color.setText(hex_color or "")
        self.color.setVisible(hex_color is not None)
        self._swatch.setVisible(hex_color is not None)
        if hex_color is not None:
            self._swatch.setStyleSheet(
                f"background: {hex_color}; border: 1px solid rgba(0, 0, 0, 0.15); border-radius: 3px;"
            )
        self.size_label.setText("" if size is None else f"Image {size[0]} × {size[1]} px")
        self.size_label.setVisible(size is not None)
