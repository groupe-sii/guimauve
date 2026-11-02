"""Text and icon buttons."""

from enum import StrEnum

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import QPushButton, QToolButton, QWidget

from guimauve.gui.element_editor.theme import METRICS, Icon, ThemeManager


class Variant(StrEnum):
    """Look of a button, read by the stylesheet."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    GHOST = "ghost"


class Button(QPushButton):
    def __init__(self, text: str = "", variant: Variant = Variant.SECONDARY, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setProperty("variant", variant.value)


class IconButton(QToolButton):
    """Square button showing only an icon, in the theme colors, with its shortcut in the tooltip.

    The shortcut is only shown: the panel that owns the button binds it, since its scope depends on the focus.
    """

    def __init__(
        self,
        name: Icon,
        theme: ThemeManager,
        tooltip: str,
        shortcut: QKeySequence | str | None = None,
        role: str = "text_secondary",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._name, self._theme, self._role = name, theme, role
        self.setToolTip(with_shortcut(tooltip, shortcut))
        self.setFixedSize(METRICS.control_height, METRICS.control_height)
        self.setIconSize(QSize(METRICS.icon, METRICS.icon))
        theme.changed.connect(self._update_icon)
        self._update_icon()

    def set_icon(self, name: Icon) -> None:
        self._name = name
        self._update_icon()

    def _update_icon(self) -> None:
        self.setIcon(self._theme.icon(self._name, self._role))


def with_shortcut(text: str, shortcut: QKeySequence | str | None) -> str:
    """Tooltip text followed by the shortcut as the system writes it, e.g. "Duplicate (Ctrl+D)"."""
    if shortcut is None:
        return text
    keys = QKeySequence(shortcut).toString(QKeySequence.SequenceFormat.NativeText)
    return f"{text} ({keys})"


class TextIconButton(Button):
    """Secondary button with an icon before its text, repainted with the theme while it exists.

    The style leaves only a few pixels between the icon and the text: the icon carries a transparent margin on its
    right, which sets the gap.
    """

    def __init__(self, text: str, name: Icon, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(text, parent=parent)
        self._name, self._theme = name, theme
        self.setIconSize(QSize(METRICS.icon + METRICS.icon_text_gap, METRICS.icon))
        theme.changed.connect(self._paint)  # a slot of the button: Qt drops it with the button
        self._paint()

    def _paint(self) -> None:
        ratio = max(self.devicePixelRatioF(), 2.0)  # sharp on a scaled screen too
        size = QSize(METRICS.icon, METRICS.icon)
        canvas = QPixmap(round((METRICS.icon + METRICS.icon_text_gap) * ratio), round(METRICS.icon * ratio))
        canvas.setDevicePixelRatio(ratio)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(0, 0, self._theme.icon(self._name, "text_secondary").pixmap(size, ratio))
        painter.end()
        self.setIcon(QIcon(canvas))


def text_icon_button(text: str, name: Icon, theme: ThemeManager) -> Button:
    """Secondary button with an icon before its text, repainted with the theme."""
    return TextIconButton(text, name, theme)
