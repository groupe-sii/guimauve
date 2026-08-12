from PySide6.QtWidgets import QVBoxLayout, QWidget

from guimauve.gui.element_editor.widgets.element.coordinates import CoordinatesGroup
from guimauve.gui.element_editor.widgets.element.name import NameGroup
from guimauve.gui.element_editor.widgets.element.properties import PropertiesGroup
from guimauve.gui.element_editor.widgets.element.variants import VariantsGroup
from guimauve.gui.element_editor.widgets.params.image import ImageParamsGroup
from guimauve.gui.element_editor.widgets.params.locate import LocateParamsGroup
from guimauve.gui.element_editor.widgets.params.match import MatchParamsGroup
from guimauve.gui.element_editor.widgets.params.mouse import MouseParamsGroup
from guimauve.gui.element_editor.widgets.params.text import TextParamsGroup


class ElementWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def load(self, element, default):
        self.grp_name.load(element)
        self.grp_coordinates.load(element)
        self.grp_variants.load(element)
        self.grp_properties.load(element, default)
        self.grp_locate.load(element, default)
        self.grp_image.load(element, default)
        self.grp_match.load(element, default)
        self.grp_mouse.load(element, default)
        self.grp_text.load(element, default)

    def _init_ui(self):
        # --- GROUPS ---
        self.grp_name = NameGroup()
        self.grp_coordinates = CoordinatesGroup()
        self.grp_variants = VariantsGroup()
        self.grp_properties = PropertiesGroup()
        self.grp_locate = LocateParamsGroup()
        self.grp_image = ImageParamsGroup()
        self.grp_mouse = MouseParamsGroup()
        self.grp_match = MatchParamsGroup()
        self.grp_text = TextParamsGroup()

        # --- ASSEMBLY ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        layout.addWidget(self.grp_name)
        layout.addWidget(self.grp_coordinates)
        layout.addWidget(self.grp_variants)
        layout.addWidget(self.grp_properties)
        layout.addWidget(self.grp_locate)
        layout.addWidget(self.grp_image)
        layout.addWidget(self.grp_mouse)
        layout.addWidget(self.grp_match)
        layout.addWidget(self.grp_text)
        layout.addStretch()
