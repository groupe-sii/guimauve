"""Icon shown as a label, in a color of the theme."""

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLabel, QWidget

from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager


class IconLabel(QLabel):
    """Icon that follows the theme, rendered at the pixel ratio of its screen."""

    def __init__(self, name: Icon, theme: ThemeManager, role: str = "text_secondary", parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self._name, self._role = name, role
        self.setFixedSize(METRICS.icon, METRICS.icon)
        theme.changed.connect(self._update)
        self._update()

    def set_icon(self, name: Icon, role: str | None = None) -> None:
        self._name = name
        self._role = role or self._role
        self._update()

    def _update(self) -> None:
        size = QSize(METRICS.icon, METRICS.icon)
        self.setPixmap(self._theme.icon(self._name, self._role).pixmap(size, self.devicePixelRatioF()))
