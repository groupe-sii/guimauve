"""Small markers of an overridden value: the violet badge and dot."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QLabel, QWidget

from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager


class Badge(QLabel):
    """Violet pill with a short text, such as the number of overridden values of a section."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setProperty("badge", "inherit")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(METRICS.badge_height)
        self.setMinimumWidth(METRICS.badge_height)


class Dot(QWidget):
    """Violet dot of a value set on the element or the variant."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedSize(QSize(METRICS.dot, METRICS.dot))
        theme.changed.connect(self.update)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._theme.palette.inherit))
        painter.drawEllipse(self.rect())
