from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton


class FloatingToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._init_ui()

        self.setStyleSheet("""
            FloatingToolbar {
                background-color: #2D2D2D;
                border: 1px solid #555555;
                border-radius: 6px;
            }
            QPushButton {
                background: transparent;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #444444; }
        """)

        self.hide()

    def anchor_to(self, rect):
        self.adjustSize()
        x = rect.center().x() - (self.width() / 2)
        y = rect.bottom() + 10
        self.move(int(x), int(y))
        self.show()

    def _init_ui(self):
        self.btn_apply = QPushButton("✓")
        self.btn_cancel = QPushButton("✕")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.btn_apply)
