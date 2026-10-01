import sys
import time

from PySide6.QtWidgets import QApplication

from guimauve.gui.replay_editor.main_window import MainWindow
from guimauve.models.replay import Replay


def start_replay_editor(replay: Replay) -> tuple[Replay, bool]:
    """Start the Replay Editor application."""
    app = QApplication()
    app.setStyle("Fusion")
    window = MainWindow(replay)
    window.show()
    app.exec()
    time.sleep(0.5)

    return window.replay, window.to_save
