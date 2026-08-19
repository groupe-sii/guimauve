from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QFormLayout, QGroupBox, QLineEdit

from guimauve.enums import MouseDirection
from guimauve.gui.common.widgets.combo_box import NoScrollComboBox
from guimauve.models.params import MouseParams


class MouseParamsGroup(QGroupBox):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("MOUSE", parent)
        self._init_ui()
        self._init_signals()

    def load(self, element, default):
        self.blockSignals(True)

        # DEFAULTS
        self.cmb_direction.setItemText(0, f"DEFAULT ({default.mouse_direction.name})")
        self.edt_speed.setPlaceholderText(f"DEFAULT ({default.mouse_speed})")

        # VALUES
        self.cmb_direction.setCurrentIndex(self.cmb_direction.findData(element.mouse_direction))
        self.edt_speed.setText(str(element.mouse_speed or ""))

        self.blockSignals(False)

    def _on_changed(self):
        speed_value = self.edt_speed.text().strip()
        if speed_value:
            speed_value = float(speed_value)
            if speed_value.is_integer():
                speed_value = int(speed_value)
        else:
            # Empty field = unset/inherit. Unlike before, "0" must stay 0 (not collapse to unset):
            # it now means "instant move", overriding an inherited non-zero speed.
            speed_value = None

        to_update = {"mouse_direction": self.cmb_direction.currentData(), "mouse_speed": speed_value}

        self.changed.emit(to_update)

    def _init_ui(self):
        # DIRECTION
        self.cmb_direction = NoScrollComboBox()
        self.cmb_direction.addItem("DEFAULT", None)
        for direction in MouseDirection:
            self.cmb_direction.addItem(direction.name, direction)

        # SPEED
        # 5000.0 is a UI-only practical cap — the model only enforces a lower bound.
        bounds = MouseParams.get_bounds("mouse_speed")
        validator = QDoubleValidator(bounds.min, 5000.0, 1, self)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.edt_speed = QLineEdit()
        self.edt_speed.setValidator(validator)

        # ASSEMBLY
        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Direction", self.cmb_direction)
        layout.addRow("Speed (px/s)", self.edt_speed)

    def _init_signals(self):
        self.cmb_direction.currentIndexChanged.connect(self._on_changed)
        self.edt_speed.textChanged.connect(self._on_changed)
