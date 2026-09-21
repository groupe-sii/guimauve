from PySide6.QtWidgets import QVBoxLayout, QWidget

from guimauve.gui.element_editor.widgets.name import NameGroup


class TextVariantWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def load(self, variant):
        self.grp_name.load(variant)

    def _init_ui(self):
        # GROUPS
        self.grp_name = NameGroup()

        # ASSEMBLY
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        layout.addWidget(self.grp_name)
        layout.addStretch()
