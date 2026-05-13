from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QGroupBox, QLineEdit


class TextParamsGroup(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("TEXT", parent)

        self._init_ui()

    def _init_ui(self):
        # THRESHOLD
        self.edt_threshold = QLineEdit()

        # LANGUAGE
        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["EN", "FR"])

        # CASE SENSITIVE
        self.chk_case_sensitive = QCheckBox()

        # ASSEMBLY
        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Threshold", self.edt_threshold)
        layout.addRow("Language", self.cmb_language)
        layout.addRow("Case sensitive", self.chk_case_sensitive)
