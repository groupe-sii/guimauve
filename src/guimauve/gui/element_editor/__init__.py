import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import QApplication, QStyleFactory

from guimauve.gui.element_editor.icons import icons
from guimauve.gui.element_editor.main_window import MainWindow
from guimauve.gui.element_editor.widgets.overlay_manager import OverlayManager
from guimauve.models.element import Element
from guimauve.models.parameters.parameters import DefaultParams

QLocale.setDefault(QLocale.c())


@dataclass
class Context:
    element: Element
    default: DefaultParams
    image_dir: str
    capture_provider: Callable
    message: str
    action: str


def start_element_editor(context: Context) -> tuple[Optional[Element], bool]:
    """
    Start the Element Editor application.

    Ensures a QApplication instance exists, injects the capture provider,
    and executes the event loop for the editor window.

    :param context: The context with the element, default parameters, the capture provider,
                    a message when GUI is triggered, etc.
    :return: The updated element or None and if it must be saved
    """
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setWindowIcon(icons.WINDOW_ICON)
    app.setStyle(QStyleFactory.create("Fusion"))

    OverlayManager.capture_provider = context.capture_provider
    OverlayManager.initial_capture = context.capture_provider()

    window = MainWindow(context)
    window.setAttribute(Qt.WA_DeleteOnClose)
    window.setWindowFlags(window.windowFlags() | Qt.WindowStaysOnTopHint)
    window.show()

    app.exec()
    time.sleep(0.5)

    return window.element_manager.element, window.to_save
