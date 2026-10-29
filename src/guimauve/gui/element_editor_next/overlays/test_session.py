"""A test result shown on the captures of all the screens, each on its own screen."""

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QCursor, QGuiApplication

from guimauve.gui.element_editor_next.overlays.geometry import fit_capture
from guimauve.gui.element_editor_next.overlays.session import WINDOW_FLAGS
from guimauve.gui.element_editor_next.overlays.test_view import ScreenView, TestView
from guimauve.gui.element_editor_next.system import ScreenMap


class TestViewSession(QObject):
    """One window per captured screen, closed together on Esc or a click.

    Each window covers its Qt screen; a remote screen, or one Qt does not show, is fitted on the primary screen. With
    several screens, each shows its number. The window showing the focused match takes the focus.

    :param views: What to draw over the capture of each screen.
    :param title: What the test found, in the banner of every screen.
    :param focused: Index of the match to show with a halo, if any.
    """

    __test__ = False  # not a test class for pytest

    finished = Signal()

    def __init__(
        self,
        views: list[ScreenView],
        screens: ScreenMap,
        title: str,
        focused: int | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.windows: dict[int, TestView] = {}
        self._focused_screen: int | None = None
        for view in views:
            screen = screens.qt_screen(view.number)
            target = screen or QGuiApplication.primaryScreen()
            shown = None
            if screen is None:  # remote, or not shown by Qt: fitted on the primary screen
                area = QRectF(0, 0, target.geometry().width(), target.geometry().height())
                shown = fit_capture(view.image.shape[1], view.image.shape[0], area)
            window = TestView(view, title, shown, focused)
            window.setWindowFlags(WINDOW_FLAGS)
            window.setScreen(target)
            window.setGeometry(target.geometry())
            window.closed.connect(self.close)
            if focused is not None and any(match.index == focused for match in view.matches):
                self._focused_screen = view.number
            self.windows[view.number] = window
        if len(self.windows) > 1:
            for number, window in self.windows.items():
                window.show_number(number)

    def start(self) -> None:
        """Shows the windows; the one with the focused match, or under the cursor, takes the focus, for Esc."""
        for window in self.windows.values():
            window.show()
        focused = self.windows.get(self._focused_screen) if self._focused_screen is not None else None
        under = QGuiApplication.screenAt(QCursor.pos())
        focused = focused or next((w for w in self.windows.values() if w.screen() is under), None)
        focused = focused or next(iter(self.windows.values()), None)
        if focused is not None:
            focused.raise_()
            focused.activateWindow()
            focused.setFocus(Qt.FocusReason.OtherFocusReason)

    def close(self) -> None:
        """Closes every window; the session is then finished."""
        if not self.windows:
            return
        for window in self.windows.values():
            window.close()
            window.deleteLater()
        self.windows = {}
        self.finished.emit()
