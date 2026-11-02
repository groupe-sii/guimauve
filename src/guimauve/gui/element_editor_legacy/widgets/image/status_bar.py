import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(28)

        self._init_ui()

    def update_mouse_pos(self, x, y):
        self.x_label.setText(f"X: {int(x) if not math.isnan(x) else '-'}")
        self.y_label.setText(f"Y: {int(y) if not math.isnan(y) else '-'}")

    def update_zoom(self, level):
        percent = int(level * 100)
        self.zoom_label.setText(f"Zoom: {percent}%")

    def update_image_size(self, width, height):
        self.size_label.setText(f"Dimensions: {int(width)} x {int(height)}")

    def _init_ui(self):
        # X POSITION
        self.x_label = QLabel("X: -")
        self.x_label.setFixedWidth(40)

        # Y POSITION
        self.y_label = QLabel("Y: -")
        self.y_label.setFixedWidth(100)

        # 2. IMAGE DIMENSIONS
        self.size_label = QLabel("Dimensions: 0 x 0")
        self.size_label.setFixedWidth(150)

        # 3. ZOOM LEVEL
        self.zoom_label = QLabel("Zoom: -%")
        self.zoom_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # ASSEMBLY
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(25)

        layout.addWidget(self.x_label)
        layout.addWidget(self.y_label)
        layout.addWidget(self.size_label)
        layout.addStretch()
        layout.addWidget(self.zoom_label)
