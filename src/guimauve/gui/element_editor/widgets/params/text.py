from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox

from guimauve.enums import OcrFidelity
from guimauve.gui.common.widgets.combo_box import NoScrollComboBox
from guimauve.gui.common.widgets.line_edit import FloatLineEdit
from guimauve.models.params import TextParams


class TextParamsGroup(QGroupBox):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("TEXT", parent)
        self._init_ui()
        self._init_signals()

    def load(self, element, default):
        self.blockSignals(True)

        # DEFAULT
        self.edt_confidence_threshold.default = default.text_confidence_threshold
        self.cmb_fidelity.setItemText(0, f"DEFAULT ({default.text_fidelity.name})")

        # VALUES
        self.edt_confidence_threshold.value = element.text_confidence_threshold
        self.cmb_fidelity.setCurrentIndex(self.cmb_fidelity.findData(element.text_fidelity))

        self.blockSignals(False)

    def _on_changed(self):
        to_update = {
            "text_confidence_threshold": self.edt_confidence_threshold.value,
            "text_fidelity": self.cmb_fidelity.currentData(),
        }

        self.changed.emit(to_update)

    def _init_ui(self):
        # THRESHOLD
        bounds = TextParams.get_bounds("text_confidence_threshold")
        self.edt_confidence_threshold = FloatLineEdit(min_val=bounds.min, max_val=bounds.max, decimals=2)

        # FIDELITY
        self.cmb_fidelity = NoScrollComboBox()
        self.cmb_fidelity.addItem("DEFAULT", None)
        for fidelity in OcrFidelity:
            self.cmb_fidelity.addItem(fidelity.name, fidelity)

        # ASSEMBLY
        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Confidence Thr.", self.edt_confidence_threshold)
        layout.addRow("Fidelity", self.cmb_fidelity)

    def _init_signals(self):
        self.edt_confidence_threshold.textChanged.connect(self._on_changed)
        self.cmb_fidelity.currentIndexChanged.connect(self._on_changed)
