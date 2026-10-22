"""Menus with titles and icons, and the button that opens one."""

from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QAction, QPainter, QPaintEvent
from PySide6.QtWidgets import QLabel, QMenu, QToolButton, QWidget, QWidgetAction

from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

CHEVRON = 12


def styled_menu(parent: QWidget | None = None) -> QMenu:
    """Menu whose items have icons, laid out for them by the stylesheet."""
    menu = QMenu(parent)
    menu.setProperty("icons", True)
    menu.setToolTipsVisible(True)
    return menu


def add_title(menu: QMenu, text: str) -> QWidgetAction:
    """Muted title above a group of items, never selected.

    QMenu.addSection draws only a line with the Fusion style and a stylesheet, without its text.
    """
    label = QLabel(text)
    label.setProperty("menuTitle", True)
    action = QWidgetAction(menu)
    action.setDefaultWidget(label)
    action.setEnabled(False)
    menu.addAction(action)
    return action


def add_item(menu: QMenu, text: str, name: Icon, theme: ThemeManager, enabled: bool = True) -> QAction:
    """Item with an icon that follows the theme."""
    action = QAction(text, menu)
    action.setEnabled(enabled)
    action.setIcon(theme.icon(name))
    theme.changed.connect(lambda: action.setIcon(theme.icon(name)))
    menu.addAction(action)
    return action


class MenuButton(QToolButton):
    """Icon followed by a chevron, opening its menu on click, e.g. the "+" of the variant list."""

    def __init__(
        self, name: Icon, theme: ThemeManager, tooltip: str, role: str = "accent", parent: QWidget | None = None
    ):
        super().__init__(parent)
        self._name, self._theme, self._role = name, theme, role
        self.setToolTip(tooltip)
        self.setProperty("noIndicator", True)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setFixedSize(METRICS.control_height + CHEVRON + METRICS.space(1), METRICS.control_height)
        theme.changed.connect(self.update)

    def sizeHint(self) -> QSize:
        return self.size()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)  # background and border from the stylesheet; the button has no icon
        painter = QPainter(self)
        size, top = METRICS.icon, (self.height() - METRICS.icon) // 2
        left = METRICS.space(2)
        self._theme.icon(self._name, self._role).paint(painter, QRect(left, top, size, size))
        chevron = self._theme.icon(Icon.CHEVRON_DOWN, self._role)
        chevron.paint(painter, QRect(left + size + 2, (self.height() - CHEVRON) // 2, CHEVRON, CHEVRON))
