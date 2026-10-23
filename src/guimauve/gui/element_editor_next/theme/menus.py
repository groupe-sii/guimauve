"""Menus with rounded corners: the stylesheet rounds their border, the window behind it must let the corners through."""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QMenu

_ROUNDED = "roundedCorners"


class RoundedMenus(QObject):
    """Makes the window of every menu transparent outside its rounded border, before the menu is first shown.

    Without it, the square corners of the native popup stay painted behind the rounded border. The system shadow
    is asked away too, since it follows the square window; Windows ignores that request and keeps its own.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Polish and isinstance(watched, QMenu):
            round_corners(watched)
        return False


def round_corners(menu: QMenu) -> None:
    """Lets the stylesheet draw the corners of the menu; call before it is shown."""
    if menu.property(_ROUNDED):  # a style may set the attribute itself, so the check uses a mark of our own
        return
    menu.setProperty(_ROUNDED, True)
    menu.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    menu.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)  # dropped by Windows, kept elsewhere
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
