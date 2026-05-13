from PySide6.QtCore import QSize
from PySide6.QtWidgets import QToolBar

from guimauve.gui.element_editor.widgets.image.toolbar.buttons.capture import CaptureButton
from guimauve.gui.element_editor.widgets.image.toolbar.buttons.crop import CropButton
from guimauve.gui.element_editor.widgets.image.toolbar.buttons.import_ import ImportButton
from guimauve.gui.element_editor.widgets.image.toolbar.buttons.test import TestButton


class ImageToolbar(QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()

        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(28, 28))

    def _init_ui(self):
        # BUTTONS
        self.btn_capture = CaptureButton()
        self.btn_import = ImportButton()
        self.btn_test = TestButton()
        self.btn_crop = CropButton()

        # ASSEMBLY
        self.addWidget(self.btn_capture)
        self.addWidget(self.btn_import)
        self.addSeparator()
        self.addWidget(self.btn_crop)
        self.addSeparator()
        self.addWidget(self.btn_test)
