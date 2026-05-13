from PySide6.QtCore import QSize
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from guimauve.gui.element_editor.icons import icons


class Options(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()

    def _init_ui(self):
        icon_size = QSize(30, 30)

        # --- SAVE ---
        self.btn_save = QToolButton()
        self.btn_save.setIcon(icons.SAVE)
        self.btn_save.setIconSize(icon_size)
        self.btn_save.setToolTip("Save <i>(Ctrl+S)<i>")
        self.btn_save.setShortcut("Ctrl+S")

        # --- SKIP ---
        self.btn_skip = QToolButton()
        self.btn_skip.setIcon(icons.SKIP)
        self.btn_skip.setIconSize(icon_size)
        self.btn_skip.setToolTip("Skip")

        # --- ASSEMBLY ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_skip)
        layout.addStretch()
