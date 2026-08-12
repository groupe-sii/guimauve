from PySide6.QtCore import QSize
from PySide6.QtWidgets import QToolBar

from guimauve.gui.element_editor.widgets.text.toolbar.buttons.test import TestButton


class TextToolbar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()

        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(28, 28))

    def _init_ui(self):
        self.btn_test = TestButton()
        self.addWidget(self.btn_test)
