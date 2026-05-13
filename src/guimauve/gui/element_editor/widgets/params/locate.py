from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QPushButton, QSizePolicy
from sugar import UNDEFINED

from guimauve.enums import ScreenArea
from guimauve.gui.common.widgets.combo_box import NoScrollComboBox
from guimauve.gui.element_editor.icons import icons
from guimauve.gui.element_editor.widgets.overlay_manager import OverlayManager
from guimauve.models.area import Area


class LocateParamsGroup(QGroupBox):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__("LOCATE", parent)

        self.default_search_area = None

        self._init_ui()
        self._init_signals()

    def load(self, element, default):
        self.blockSignals(True)

        # DEFAULTS
        name = default.search_area.name if isinstance(default.search_area, ScreenArea) else "CUSTOM..."
        self.cmb_search_area.setItemText(0, f"DEFAULT ({name})")
        self.default_search_area = default.search_area

        # VALUES
        val = element.search_area
        index = self.cmb_search_area.findData(val)

        if index != -1:
            self.cmb_search_area.setCurrentIndex(index)
        elif isinstance(val, Area):
            custom_idx = 1
            self.cmb_search_area.setItemData(custom_idx, val)
            self.cmb_search_area.setCurrentIndex(custom_idx)
        else:
            self.cmb_search_area.setCurrentIndex(0)

        self.blockSignals(False)

    def _handle_selection(self, index):
        data = self.cmb_search_area.itemData(index)

        if index == 1 or isinstance(data, Area):
            windows = self.window().get_visible_windows()
            self.overlay = OverlayManager()
            self.overlay.rect_selected.connect(self._on_area_selected)
            self.overlay.select_area(windows_to_hide=windows)
        else:
            self._on_changed()

    def _on_area_selected(self, rect):
        if rect and rect.isValid():
            custom_idx = 1

            area = Area(top=rect.top(), left=rect.left(), right=rect.right(), bottom=rect.bottom())

            self.cmb_search_area.setItemData(custom_idx, area)
            self.cmb_search_area.setCurrentIndex(custom_idx)
        else:
            self.cmb_search_area.setCurrentIndex(0)

        self._on_changed()

    def _on_view_clicked(self):
        area = self.cmb_search_area.currentData()

        if area is UNDEFINED:
            area = self.default_search_area
        if isinstance(area, ScreenArea):
            h, w, _ = OverlayManager.initial_capture.shape
            area = area.get_area((w, h))

        windows = self.window().get_visible_windows()

        self.viewer = OverlayManager()
        self.viewer.visualize(area, windows_to_hide=windows)

    def _on_changed(self):
        search_area = self.cmb_search_area.currentData()

        to_update = {
            "search_area": search_area,
        }

        self.changed.emit(to_update)

    def _init_ui(self):
        # SEARCH AREA
        self.cmb_search_area = NoScrollComboBox()
        self.cmb_search_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.cmb_search_area.addItem("DEFAULT", UNDEFINED)
        self.cmb_search_area.addItem("CUSTOM...")
        for area in ScreenArea:
            self.cmb_search_area.addItem(area.name, area)

        self.btn_view_area = QPushButton()
        self.btn_view_area.setIcon(icons.VIEW)
        self.btn_view_area.setToolTip("Visualize area")

        area_layout = QHBoxLayout()
        area_layout.addWidget(self.cmb_search_area)
        area_layout.addWidget(self.btn_view_area)

        # ASSEMBLY
        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignRight)
        layout.addRow("Search area", area_layout)

    def _init_signals(self):
        self.cmb_search_area.activated.connect(self._handle_selection)
        self.btn_view_area.clicked.connect(self._on_view_clicked)
