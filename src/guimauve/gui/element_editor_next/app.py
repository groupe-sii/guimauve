"""Running the editor: the Qt application, the theme and the window, until the window closes."""

import sys

from PySide6.QtCore import QEventLoop, QSettings
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.contract import Context, EditorResult
from guimauve.gui.element_editor_next.services import CaptureService
from guimauve.gui.element_editor_next.state import Document, Store
from guimauve.gui.element_editor_next.system import ScreenMap, keep_on_top
from guimauve.gui.element_editor_next.theme import ThemeManager, logo
from guimauve.gui.element_editor_next.window import EditorWindow

SETTINGS = ("guimauve", "element_editor")

_theme: tuple[QApplication, ThemeManager] | None = None
"""Theme of the running application, kept from one opening of the editor to the next."""


def run(context: Context) -> EditorResult:
    """Opens the editor on the context and returns once its window is closed."""
    app = _application()
    settings = QSettings(*SETTINGS)
    store = Store(Document(context.element, context.code_overrides), context.default, context.screens)
    capture = CaptureService(context.capture_provider, ScreenMap(context.screens))
    capture.take_initial()  # before the window shows, so it is in none of them
    window = EditorWindow(store, _theme_of(app, settings), settings, context, capture)
    capture.set_windows([window])

    loop = QEventLoop()  # also works when an application is already running its own loop
    window.finished.connect(loop.quit)
    keep_on_top(window)
    window.show()  # in the screenshots of the user; out_of_capture only around the captures of the editor
    window.raise_()
    window.activateWindow()
    loop.exec()
    capture.shutdown()  # a capture still running ends before its thread goes

    assert window.result is not None  # set before finished
    window.deleteLater()
    return window.result


def _application() -> QApplication:
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication(sys.argv[:1] or ["guimauve"])
    app.setWindowIcon(logo())
    return app


def _theme_of(app: QApplication, settings: QSettings) -> ThemeManager:
    global _theme
    if _theme is None or _theme[0] is not app:
        theme = ThemeManager(app, settings)
        theme.apply()
        _theme = (app, theme)
    return _theme[1]
