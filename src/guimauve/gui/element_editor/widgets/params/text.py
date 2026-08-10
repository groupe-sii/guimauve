from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLineEdit


class TextParamsGroup(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("TEXT", parent)

        self._init_ui()

    def _init_ui(self):
        # THRESHOLD
        self.edt_threshold = QLineEdit()

        # ASSEMBLY
        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Threshold", self.edt_threshold)
