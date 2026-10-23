"""Window behaviors that depend on the system: staying out of captures, staying on top, focus."""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.system import windows
from guimauve.gui.element_editor_next.system.detect import Platform, current_platform

HIDE_DELAY_MS = 300
"""Time left to the system to remove a hidden window from the screen before a capture."""

EXCLUDE_DELAY_MS = 50
"""Time left to the compositor to apply the exclusion, a few frames, before a capture."""

_EXCLUDED = "excludedFromCapture"


def is_excluded_from_capture(window: QWidget) -> bool:
    return bool(window.property(_EXCLUDED))


@contextmanager
def out_of_capture(targets: Sequence[QWidget]) -> Iterator[None]:
    """Keeps the visible windows out of the captures taken inside the block, then puts them back.

    The windows stay on screen, excluded from captures by the system on Windows; elsewhere, or when the exclusion
    fails, they are hidden. Outside the block, the windows appear in every capture, such as the screenshots the
    user takes. For a capture after a delay, the block covers the countdown too.
    """
    excluded = [window for window in targets if window.isVisible() and _set_excluded(window, True)]
    hidden = [window for window in targets if window.isVisible() and window not in excluded]
    for window in hidden:
        window.hide()
    if hidden or excluded:
        _wait(HIDE_DELAY_MS if hidden else EXCLUDE_DELAY_MS)
    try:
        yield
    finally:
        for window in excluded:
            _set_excluded(window, False)
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
    if is_excluded_from_capture(window):  # changed during a capture
        _set_excluded(window, True)
    if visible:
        window.show()


def _set_excluded(window: QWidget, excluded: bool) -> bool:
    """Asks the system to exclude the window from captures, or to include it again; False when it cannot."""
    done = current_platform() is Platform.WINDOWS and windows.set_excluded_from_capture(int(window.winId()), excluded)
    window.setProperty(_EXCLUDED, excluded and done)
    return done


def _wait(milliseconds: int) -> None:
    """Lets Qt repaint for a while without handling user input, unlike time.sleep which freezes the interface."""
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
