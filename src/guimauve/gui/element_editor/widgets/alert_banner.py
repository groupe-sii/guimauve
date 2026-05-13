from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


class AlertBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AlertBanner")
        self.setFixedHeight(35)
        self._init_ui()
        self.hide()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame#AlertBanner {
                background-color: rgba(255, 102, 0, 0.1);
                border-bottom: 2px solid #FF6600;
                margin-bottom: 2px;
            }
            QLabel {
                font-size: 14px;
                font-weight: 700;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)

        self.lbl_message = QLabel("")
        layout.addWidget(self.lbl_message)
        layout.addStretch()

    def set_alert(self, alert: str):
        self.lbl_message.setText(f"⚠️ {alert}")
        self.show()
