from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import QMenu, QToolButton

from guimauve.gui.element_editor.icons import icons
from guimauve.gui.element_editor.widgets.overlay_manager import OverlayManager


class CaptureButton(QToolButton):
    image_ready = Signal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()
        self._init_signals()

        self.setIcon(icons.CAPTURE)
        self.setToolTip("Capture")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setAutoRaise(True)

    def _trigger_capture(self, delay=0):
        """Initializes and starts the capture overlay."""
        windows = self.window().get_visible_windows()
        self.overlay = OverlayManager()
        self.overlay.image_captured.connect(self._on_image_ready)
        self.overlay.capture_image(delay=delay, windows_to_hide=windows)

    def _on_image_ready(self, pixmap):
        """Handle the final cropped image."""
        self.image_ready.emit(pixmap)

    def _init_ui(self):
        menu = QMenu(self)

        self.act_instant = QAction("Instant", icon=icons.INSTANT, parent=self)
        self.act_initial = QAction("Initial", icon=icons.INITIAL, parent=self)

        delay_menu = QMenu("Delay", icon=icons.TIMER, parent=self)

        self.act_delay_3s = QAction("3 sec", self)
        self.act_delay_5s = QAction("5 sec", self)
        self.act_delay_10s = QAction("10 sec", self)

        delay_menu.addActions([self.act_delay_3s, self.act_delay_5s, self.act_delay_10s])

        menu.addAction(self.act_instant)
        menu.addAction(self.act_initial)
        menu.addMenu(delay_menu)

        self.setMenu(menu)

    def _init_signals(self):
        self.act_instant.triggered.connect(self._trigger_capture)
        self.act_initial.triggered.connect(lambda: self._trigger_capture(-1))

        self.act_delay_3s.triggered.connect(lambda: self._trigger_capture(3))
        self.act_delay_5s.triggered.connect(lambda: self._trigger_capture(5))
        self.act_delay_10s.triggered.connect(lambda: self._trigger_capture(10))
