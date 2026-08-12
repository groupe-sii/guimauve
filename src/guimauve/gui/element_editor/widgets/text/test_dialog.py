from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout

from guimauve.enums import OcrFidelity
from guimauve.gui.common.widgets.combo_box import NoScrollComboBox
from guimauve.gui.common.widgets.line_edit import FloatLineEdit


class TextTestDialog(QDialog):
    test_requested = Signal(dict)

    def __init__(self, default, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Test Parameters")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setFixedSize(280, 220)

        self.default = default

        self._init_ui()
        self._init_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- PARAMS ---
        form = QFormLayout()

        self.edt_confidence_threshold = FloatLineEdit(min_val=0.0, max_val=1.0)
        self.cmb_fidelity = NoScrollComboBox()
        for fidelity in OcrFidelity:
            self.cmb_fidelity.addItem(fidelity.name, fidelity)

        self.edt_confidence_threshold.value = self.default.text_confidence_threshold
        self.cmb_fidelity.setCurrentIndex(self.cmb_fidelity.findData(self.default.text_fidelity))

        form.addRow("Confidence Thr.", self.edt_confidence_threshold)
        form.addRow("Fidelity", self.cmb_fidelity)

        layout.addLayout(form)

        # --- ACTIONS / RESULTS ---
        self.btn_test = QPushButton("Run Test")
        self.btn_test.setMinimumHeight(35)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setFixedHeight(4)

        self.lbl_result = QLabel("")
        self.lbl_result.setAlignment(Qt.AlignCenter)
        self.lbl_result.setStyleSheet("font-weight: bold;")

        layout.addWidget(self.btn_test)
        layout.addWidget(self.progress)
        layout.addWidget(self.lbl_result)

    def _init_signals(self):
        self.btn_test.clicked.connect(self._on_test)

    def _on_test(self):
        params = {
            "confidence_threshold": self.edt_confidence_threshold.value,
            "fidelity": self.cmb_fidelity.currentData(),
        }

        self.set_running(True)
        self.test_requested.emit(params)

    def set_running(self, running: bool):
        self.btn_test.setEnabled(not running)
        self.progress.setVisible(running)
        if running:
            self.lbl_result.setText("Processing...")
            self.lbl_result.setStyleSheet("color: gray;")

    def set_result(self, count: int):
        self.set_running(False)
        if count == 0:
            self.lbl_result.setText("No match")
            self.lbl_result.setStyleSheet("color: #e05252;")
        else:
            self.lbl_result.setText(f"{count} match{'es' if count > 1 else ''}")
            self.lbl_result.setStyleSheet("color: #52b052;")
