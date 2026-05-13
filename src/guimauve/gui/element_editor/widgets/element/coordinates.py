from PySide6.QtCore import Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit
from sugar import UNDEFINED


class CoordinatesGroup(QGroupBox):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("COORDINATES", parent)
        self._init_ui()
        self._init_signals()

    def load(self, element) -> None:
        self.blockSignals(True)
        self.edt_x.setText(str(element.x or element.rel_x or ""))
        self.edt_y.setText(str(element.y or element.rel_y or ""))
        self.chk_rel_x.setChecked(bool(element.rel_x))
        self.chk_rel_y.setChecked(bool(element.rel_y))
        self.blockSignals(False)

    def _on_changed(self):
        is_rel_x = self.chk_rel_x.isChecked()
        is_rel_y = self.chk_rel_y.isChecked()

        val_x = int(self.edt_x.text()) if self.edt_x.text().strip() else UNDEFINED
        val_y = int(self.edt_y.text()) if self.edt_y.text().strip() else UNDEFINED

        to_update = {
            "x": val_x if not is_rel_x else UNDEFINED,
            "rel_x": val_x if is_rel_x else UNDEFINED,
            "y": val_y if not is_rel_y else UNDEFINED,
            "rel_y": val_y if is_rel_y else UNDEFINED,
        }

        self.changed.emit(to_update)

    def _init_ui(self):
        # X
        self.edt_x = QLineEdit()
        self.edt_x.setValidator(QIntValidator())
        self.edt_x.setPlaceholderText("-")
        self.chk_rel_x = QCheckBox("Relative")

        # Y
        self.edt_y = QLineEdit()
        self.edt_y.setValidator(QIntValidator())
        self.edt_y.setPlaceholderText("-")
        self.chk_rel_y = QCheckBox("Relative")

        # ASSEMBLY
        x_layout = QHBoxLayout()
        x_layout.addWidget(self.edt_x, 1)
        x_layout.addWidget(self.chk_rel_x)

        y_layout = QHBoxLayout()
        y_layout.addWidget(self.edt_y, 1)
        y_layout.addWidget(self.chk_rel_y)

        layout = QFormLayout(self)
        layout.addRow("X", x_layout)
        layout.addRow("Y", y_layout)

    def _init_signals(self):
        self.edt_x.textChanged.connect(self._on_changed)
        self.edt_y.textChanged.connect(self._on_changed)
        self.chk_rel_x.stateChanged.connect(self._on_changed)
        self.chk_rel_y.stateChanged.connect(self._on_changed)
