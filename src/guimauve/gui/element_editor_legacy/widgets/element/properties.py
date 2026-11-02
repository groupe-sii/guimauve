from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox

from guimauve.gui.common.widgets.combo_box import YesNoComboBox
from guimauve.gui.common.widgets.line_edit import FloatLineEdit, StringLineEdit


class PropertiesGroup(QGroupBox):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("PROPERTIES", parent)
        self._init_ui()
        self._init_signals()

    def load(self, element, default):
        self.blockSignals(True)

        # DEFAULTS
        self.edt_timeout.default = default.timeout
        self.edt_target.default = default.target
        self.cmb_find_all.default = default.find_all

        # VALUES
        self.edt_timeout.value = element.timeout
        self.edt_target.value = element.target
        self.cmb_find_all.value = element.find_all

        self.blockSignals(False)

    def _on_changed(self):
        to_update = {
            "timeout": self.edt_timeout.value,
            "target": self.edt_target.value,
            "find_all": self.cmb_find_all.value,
        }

        self.changed.emit(to_update)

    def _init_ui(self):
        self.edt_timeout = FloatLineEdit(min_val=0.1, max_val=999.9, decimals=1)
        self.edt_target = StringLineEdit()
        self.cmb_find_all = YesNoComboBox()

        # ASSEMBLY
        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Timeout (s)", self.edt_timeout)
        layout.addRow("Target", self.edt_target)
        layout.addRow("Find all", self.cmb_find_all)

    def _init_signals(self):
        self.edt_timeout.textChanged.connect(self._on_changed)
        self.edt_target.textChanged.connect(self._on_changed)
        self.cmb_find_all.currentIndexChanged.connect(self._on_changed)
