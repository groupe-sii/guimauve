from PySide6.QtWidgets import QToolButton

from guimauve.gui.element_editor.icons import icons


class ImportButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setIcon(icons.IMPORT)
        self.setToolTip("Import")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setAutoRaise(True)
