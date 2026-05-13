from PySide6.QtWidgets import QVBoxLayout, QWidget

from guimauve.gui.element_editor.widgets.params.image import ImageParamsGroup
from guimauve.gui.element_editor.widgets.params.match import MatchParamsGroup
from guimauve.gui.element_editor.widgets.params.mouse import MouseParamsGroup
from guimauve.gui.element_editor.widgets.variants.image.properties import PropertiesGroup
from guimauve.gui.element_editor.widgets.variants.image.targets import TargetsGroup


class ImageVariantWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def load(self, variant, image_dir):
        self.grp_properties.load(variant, image_dir)
        self.grp_targets.load(variant)

    def _init_ui(self):
        # GROUPS
        self.grp_properties = PropertiesGroup()
        self.grp_targets = TargetsGroup()
        self.grp_image = ImageParamsGroup()
        self.grp_mouse = MouseParamsGroup()
        self.grp_match = MatchParamsGroup()

        self.grp_image.setVisible(False)
        self.grp_mouse.setVisible(False)
        self.grp_match.setVisible(False)

        # ASSEMBLY
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        layout.addWidget(self.grp_properties)
        layout.addWidget(self.grp_targets)
        layout.addWidget(self.grp_image)
        layout.addWidget(self.grp_mouse)
        layout.addWidget(self.grp_match)
        layout.addStretch()
