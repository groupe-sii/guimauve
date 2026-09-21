from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QWidget,
)

from guimauve.gui.element_editor.icons import icons


class PropertiesGroup(QGroupBox):
    changed = Signal(dict)
    match_area_requested = Signal(object)
    match_area_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__("PROPERTIES", parent)
        self._init_ui()
        self._init_signals()

    def load(self, variant):
        # VALUES
        self.blockSignals(True)
        self.edt_default_target.setText(variant.default_target or "")
        self.blockSignals(False)

        self.update_match_area_label(variant.match_area)

        if variant.match_area:
            self.match_area_requested.emit(variant.match_area)

    def update_match_area_label(self, area):
        if area:
            self.lbl_match_area.setText(f"L: {area.left}, T: {area.top}, R: {area.right}, B: {area.bottom}")
        else:
            self.lbl_match_area.setText("-")
        self.btn_clear_area.setEnabled(bool(area))

    def _on_edit_area_clicked(self):
        self.update_match_area_label(None)
        self.match_area_cleared.emit()

    def _on_clear_area_clicked(self):
        self.update_match_area_label(None)
        self.match_area_cleared.emit()

    def _on_changed(self):
        to_update = {
            "default_target": self.edt_default_target.text().strip() or None,
        }

        self.changed.emit(to_update)

    def _init_ui(self):
        icon_size = QSize(20, 20)

        # MATCH AREA
        self.area_container = QWidget()
        area_layout = QHBoxLayout(self.area_container)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_layout.setSpacing(4)

        self.lbl_match_area = QLabel("-")

        self.btn_edit_area = QToolButton()
        self.btn_edit_area.setIcon(icons.EDIT)
        self.btn_edit_area.setIconSize(icon_size)
        self.btn_edit_area.setToolTip("Define match area")
        self.btn_edit_area.setAutoRaise(True)

        self.btn_clear_area = QToolButton()
        self.btn_clear_area.setIcon(icons.REMOVE)
        self.btn_clear_area.setIconSize(icon_size)
        self.btn_clear_area.setToolTip("Clear match area")
        self.btn_clear_area.setAutoRaise(True)

        area_layout.addWidget(self.lbl_match_area, 1)
        area_layout.addWidget(self.btn_edit_area)
        area_layout.addWidget(self.btn_clear_area)

        # DEFAULT TARGET
        self.edt_default_target = QLineEdit()

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Match area", self.area_container)
        layout.addRow("Default target", self.edt_default_target)

    def _init_signals(self):
        self.edt_default_target.textChanged.connect(self._on_changed)
        self.btn_edit_area.clicked.connect(lambda: self.match_area_requested.emit(None))
        self.btn_clear_area.clicked.connect(self._on_clear_area_clicked)
