"""Window behaviors that depend on the system: exclusion from captures, staying on top, focus."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.system import windows
from guimauve.gui.element_editor_next.system.detect import Platform, current_platform

HIDE_DELAY_MS = 300
"""Time left to the system to remove a hidden window from the screen before a capture."""

_EXCLUDED = "excludedFromCapture"


def exclude_from_capture(window: QWidget) -> bool:
    """Keeps the window visible on screen but out of screen captures; returns False when the system cannot.

    Changing the window flags recreates the native window and loses the exclusion: keep_on_top and
    show_without_focus apply it again. When this returns False, wrap captures in hidden_during_capture.
    """
    excluded = current_platform() is Platform.WINDOWS and windows.exclude_from_capture(int(window.winId()))
    window.setProperty(_EXCLUDED, excluded)
    return excluded


def is_excluded_from_capture(window: QWidget) -> bool:
    return bool(window.property(_EXCLUDED))


@contextmanager
def hidden_during_capture(windows: Sequence[QWidget]) -> Iterator[None]:
    """Hides the visible windows that are not excluded from captures, for the time of a capture."""
    hidden = [window for window in windows if window.isVisible() and not is_excluded_from_capture(window)]
    for window in hidden:
        window.hide()
    if hidden:
        _wait(HIDE_DELAY_MS)
    try:
        yield
    finally:
        for window in hidden:
            window.show()


def keep_on_top(window: QWidget) -> None:
    """Keeps the window above the others; some Wayland compositors ignore it."""
    _set_flag(window, Qt.WindowType.WindowStaysOnTopHint)


def show_without_focus(window: QWidget) -> None:
    """Shows the window without taking the focus from the application in use; may be ignored on Wayland."""
    window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    _set_flag(window, Qt.WindowType.WindowDoesNotAcceptFocus)
    window.show()


def _set_flag(window: QWidget, flag: Qt.WindowType) -> None:
    visible = window.isVisible()
    window.setWindowFlag(flag, True)  # recreates the native window, which hides it
    if is_excluded_from_capture(window):
        exclude_from_capture(window)
    if visible:
        window.show()


def _wait(milliseconds: int) -> None:
    """Lets Qt repaint for a while without handling user input, unlike time.sleep which freezes the interface."""
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
