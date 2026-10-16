"""Text and icon buttons."""

from enum import StrEnum

from PySide6.QtCore import QSize
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QPushButton, QToolButton, QWidget

from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager


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

    def _update_icon(self) -> None:
        self.setIcon(self._theme.icon(self._name, self._role))


def with_shortcut(text: str, shortcut: QKeySequence | str | None) -> str:
    """Tooltip text followed by the shortcut as the system writes it, e.g. "Duplicate (Ctrl+D)"."""
    if shortcut is None:
        return text
    keys = QKeySequence(shortcut).toString(QKeySequence.SequenceFormat.NativeText)
    return f"{text} ({keys})"
