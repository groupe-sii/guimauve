from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox
from sugar import UNDEFINED

from guimauve.enums import MatchSort
from guimauve.gui.common.widgets.combo_box import NoScrollComboBox
from guimauve.gui.common.widgets.line_edit import IntLineEdit


class MatchParamsGroup(QGroupBox):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("MATCH", parent)
        self._init_ui()
        self._init_signals()

    def load(self, element, default):
        self.blockSignals(True)

        # DEFAULT
        self.edt_index.default = default.match_index
        self.cmb_sort.setItemText(0, f"DEFAULT ({default.match_sort.name})")

        # VALUES
        self.edt_index.value = element.match_index
        self.cmb_sort.setCurrentIndex(self.cmb_sort.findData(element.match_sort))

        self.blockSignals(False)

    def _on_changed(self):
        to_update = {"match_index": self.edt_index.value, "match_sort": self.cmb_sort.currentData()}

        self.changed.emit(to_update)

    def _init_ui(self):
        # INDEX
        self.edt_index = IntLineEdit(min_val=0, max_val=1000)

        # SORT
        self.cmb_sort = NoScrollComboBox()
        self.cmb_sort.addItem("DEFAULT", UNDEFINED)
        for sort in MatchSort:
            self.cmb_sort.addItem(sort.name, sort)

        # ASSEMBLY
        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Index", self.edt_index)
        layout.addRow("Sort", self.cmb_sort)

    def _init_signals(self):
        self.edt_index.textChanged.connect(self._on_changed)
        self.cmb_sort.currentIndexChanged.connect(self._on_changed)
