from PySide6.QtWidgets import QComboBox
from sugar import UNDEFINED


class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()


class YesNoComboBox(NoScrollComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._default = UNDEFINED

        self.addItem("", UNDEFINED)
        self.addItem("YES", True)
        self.addItem("NO", False)

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, default):
        default_text = "YES" if default else "NO"
        self.setItemText(0, f"DEFAULT ({default_text})")
        self._default = default

    @property
    def value(self):
        return self.currentData()

    @value.setter
    def value(self, value):
        self.setCurrentIndex(self.findData(value))
