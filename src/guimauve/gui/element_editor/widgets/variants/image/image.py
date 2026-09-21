from PySide6.QtWidgets import QVBoxLayout, QWidget

from guimauve.gui.element_editor.widgets.name import NameGroup
from guimauve.gui.element_editor.widgets.params.image import ImagePropertiesGroup
from guimauve.gui.element_editor.widgets.params.match import MatchPropertiesGroup
from guimauve.gui.element_editor.widgets.params.mouse import MousePropertiesGroup
from guimauve.gui.element_editor.widgets.variants.image.properties import PropertiesGroup
from guimauve.gui.element_editor.widgets.variants.image.targets import TargetsGroup


class ImageVariantWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def load(self, variant):
        self.grp_name.load(variant)
        self.grp_properties.load(variant)
        self.grp_targets.load(variant)

    def _init_ui(self):
        # GROUPS
        self.grp_name = NameGroup()
        self.grp_properties = PropertiesGroup()
        self.grp_targets = TargetsGroup()
        self.grp_image = ImagePropertiesGroup()
        self.grp_mouse = MousePropertiesGroup()
        self.grp_match = MatchPropertiesGroup()

        self.grp_image.setVisible(False)
        self.grp_mouse.setVisible(False)
        self.grp_match.setVisible(False)

        # ASSEMBLY
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        layout.addWidget(self.grp_name)
        layout.addWidget(self.grp_properties)
        layout.addWidget(self.grp_targets)
        layout.addWidget(self.grp_image)
        layout.addWidget(self.grp_mouse)
        layout.addWidget(self.grp_match)
        layout.addStretch()
