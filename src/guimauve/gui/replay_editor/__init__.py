import logging
import sys
import time
from typing import Optional

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QApplication

from guimauve.gui.replay_editor.main_window import MainWindow
from guimauve.models.replay import Replay

logger = logging.getLogger(__name__)


def start_replay_editor(replay: Replay | None = None) -> tuple[Replay | None, bool]:
    """Start the Replay Editor application."""
    app = QApplication()
    app.setStyle("Fusion")
    window = MainWindow(replay)
    window.setWindowFlags(window.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    name = replay.name if replay is not None else None
    logger.debug("Replay editor opened for %s", name)
    window.show()
    app.exec()
    time.sleep(0.5)
    logger.debug("Replay editor closed for %s: %s", name, "saved" if window.to_save else "nothing to save")

    return window.replay, window.to_save
