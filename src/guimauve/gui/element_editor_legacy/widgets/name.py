from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout


class NameGroup(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("NAME", parent)
        self._init_ui()

    def load(self, element):
        self.lbl_name.setText(element.name)

    def _init_ui(self):
        # NAME
        self.lbl_name = QLabel("-")
        self.lbl_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.lbl_name.setAlignment(Qt.AlignCenter)

        # ASSEMBLY
        layout = QVBoxLayout(self)
        layout.addWidget(self.lbl_name)
