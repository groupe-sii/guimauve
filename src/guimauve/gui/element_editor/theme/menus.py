"""Menus and popups with rounded corners: the stylesheet rounds their border, the window behind must let the corners
through."""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QMenu, QWidget

_ROUNDED = "roundedCorners"
_LIST_POPUP = "QComboBoxPrivateContainer"
"""Window that Qt makes for the popup of a drop-down list."""


class RoundedMenus(QObject):
    """Makes the window of every menu and every popup of a list transparent outside its rounded border, before it is
    first shown.

    Without it, the square corners of the native popup stay painted behind the rounded border. The system shadow
    is asked away too, since it follows the square window; Windows ignores that request and keeps its own.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Polish and (isinstance(watched, QMenu) or watched.inherits(_LIST_POPUP)):
            assert isinstance(watched, QWidget)
            round_corners(watched)
        return False


def round_corners(popup: QWidget) -> None:
    """Lets the stylesheet draw the corners of a menu or another popup window; call before it is shown."""
    if popup.property(_ROUNDED):  # a style may set the attribute itself, so the check uses a mark of our own
        return
    popup.setProperty(_ROUNDED, True)
    popup.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    popup.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, True)  # dropped by Windows, kept elsewhere
    popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
