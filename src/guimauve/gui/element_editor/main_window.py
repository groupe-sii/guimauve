from copy import deepcopy

import numpy as np
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QScrollArea, QStackedWidget, QVBoxLayout, QWidget
from sugar import UNDEFINED

from guimauve.gui.common.resources import ndarray_to_qpixmap, qpixmap_to_ndarray
from guimauve.gui.element_editor.element_manager import ElementManager
from guimauve.gui.element_editor.widgets.alert_banner import AlertBanner
from guimauve.gui.element_editor.widgets.element.element import ElementWidget
from guimauve.gui.element_editor.widgets.image.editor import ImageEditor
from guimauve.gui.element_editor.widgets.options import Options
from guimauve.gui.element_editor.widgets.text.editor import TextEditor
from guimauve.gui.element_editor.widgets.variants.image.image import ImageVariantWidget
from guimauve.models.variant import ImageVariant, TextVariant


class MainWindow(QMainWindow):
    def __init__(self, context):
        super().__init__()

        self.element_manager = ElementManager()
        self.to_save = None
        self.context = context

        self.setWindowTitle("Element editor")

        self._init_ui()
        self._init_signals()
        self._load_settings()

        self.set_variant_edition_visible(False)

        element = deepcopy(context.element)
        self.element_manager.load(element, context.default)
        if element.variants:
            self._switch_variant(element.variants[0])

        if context.message:
            self.alert_banner.set_alert(f"{context.message} | Action: {context.action}")

    def get_visible_windows(self):
        windows = [self]
        for dock in self.findChildren(QDockWidget):
            if dock.isFloating() and dock.isVisible():
                windows.append(dock)
        return windows

    def closeEvent(self, event):
        """Triggered automatically when the window is closed."""
        self._save_settings()
        super().closeEvent(event)

    def _on_click_save(self):
        self.to_save = True
        self.close()

    def _on_click_skip(self):
        self.to_save = False
        self.close()

    def _switch_variant(self, variant):
        if isinstance(variant, ImageVariant):
            self.stack_editors.setCurrentWidget(self.image_editor)
            self.stack_variant.setCurrentWidget(self.image_variant)
            self.image_editor.viewer.remove_match_area()
            self.image_editor.clear_targets()
            self.image_editor.remove_image()
            self.image_editor.status_bar.update_image_size(0, 0)
            self.image_editor.status_bar.update_zoom(1)
            if isinstance(variant.image, np.ndarray):
                pixmap = ndarray_to_qpixmap(variant.image)
                self.image_editor.load_image(pixmap)
            self.image_variant.load(variant, self.context.image_dir)

        elif isinstance(variant, TextVariant):
            self.stack_editors.setCurrentWidget(self.text_editor)
            self.stack_variant.setCurrentWidget(self.text_variant)
            self.text_editor.load(variant)

        self.set_variant_edition_visible(True)

    def set_variant_edition_visible(self, visible):
        self.stack_editors.setVisible(visible)
        self.dock_variant.setVisible(visible)

    def _on_variant_added(self, variant):
        self._switch_variant(variant)

    def _on_variant_selected(self, variant):
        self._switch_variant(variant)

    def _on_variant_removed(self, _, next_variant):
        if next_variant is not None:
            self._switch_variant(next_variant)
        if next_variant is None:
            self.set_variant_edition_visible(False)

    def _init_ui(self):
        # --- ALERT BANNER ---
        self.alert_banner = AlertBanner()

        # --- EDITORS ---
        self.image_editor = ImageEditor()
        self.text_editor = TextEditor()

        self.stack_editors = QStackedWidget()
        self.stack_editors.addWidget(self.image_editor)
        self.stack_editors.addWidget(self.text_editor)

        # --- ELEMENT ---
        self.element = ElementWidget()

        self.element_scroll_area = QScrollArea()
        self.element_scroll_area.setWidgetResizable(True)
        self.element_scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.element_scroll_area.setWidget(self.element)

        self.dock_element = QDockWidget("ELEMENT", self)
        self.dock_element.setObjectName("dock_element")
        self.dock_element.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.dock_element.setWidget(self.element_scroll_area)

        # --- VARIANT ---
        self.image_variant = ImageVariantWidget()
        self.text_variant = QWidget()

        self.stack_variant = QStackedWidget()
        self.stack_variant.addWidget(self.image_variant)
        self.stack_variant.addWidget(self.text_variant)

        self.variant_scroll_area = QScrollArea()
        self.variant_scroll_area.setWidgetResizable(True)
        self.variant_scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.variant_scroll_area.setWidget(self.stack_variant)

        self.dock_variant = QDockWidget("VARIANT", self)
        self.dock_variant.setObjectName("dock_variant")
        self.dock_variant.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.dock_variant.setWidget(self.variant_scroll_area)

        # --- OPTIONS ---
        self.options = Options()

        self.dock_options = QDockWidget("OPTIONS", self)
        self.dock_options.setObjectName("dock_options")
        self.dock_options.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.dock_options.setWidget(self.options)

        # --- ASSEMBLY ---
        self.center_container = QWidget()
        center_layout = QVBoxLayout(self.center_container)
        center_layout.setAlignment(Qt.AlignTop)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(self.alert_banner)
        center_layout.addWidget(self.stack_editors)

        self.setCentralWidget(self.center_container)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_options)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_element)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_variant)

    def _init_signals(self):
        # OPTIONS
        self.options.btn_save.clicked.connect(self._on_click_save)
        self.options.btn_skip.clicked.connect(self._on_click_skip)

        # ELEMENT LOADED
        self.element_manager.element_loaded.connect(self.element.load)

        # ELEMENT EDITED
        self.element.grp_coordinates.changed.connect(self.element_manager.update_properties)
        self.element.grp_properties.changed.connect(self.element_manager.update_properties)
        self.element.grp_locate.changed.connect(self.element_manager.update_properties)
        self.element.grp_mouse.changed.connect(self.element_manager.update_properties)
        self.element.grp_match.changed.connect(self.element_manager.update_properties)
        self.element.grp_image.changed.connect(self.element_manager.update_properties)
        self.element.grp_text.changed.connect(self.element_manager.update_properties)

        # VARIANTS ORDER
        self.element.grp_variants.variants_order_changed.connect(
            lambda variants: self.element_manager.update_properties({"variants": variants})
        )

        # VARIANT EDITED
        self.element_manager.variant_added.connect(self._on_variant_added)
        self.element_manager.variant_selected.connect(self._on_variant_selected)
        self.element_manager.variant_removed.connect(self._on_variant_removed)

        self.element.grp_variants.variant_added.connect(self.element_manager.add_variant)
        self.element.grp_variants.variant_selected.connect(self.element_manager.select_variant)
        self.element.grp_variants.variant_removed.connect(self.element_manager.remove_variant)

        self.image_variant.grp_properties.changed.connect(self.element_manager.update_variant)
        self.text_editor.changed.connect(self.element_manager.update_variant)

        self.image_editor.captured_image_loaded.connect(
            lambda pixmap: self.element_manager.update_variant(
                {"image": qpixmap_to_ndarray(pixmap), "targets": UNDEFINED}
            )
        )

        self.image_editor.crop_applied.connect(
            lambda pixmap: self.element_manager.update_variant({"image": qpixmap_to_ndarray(pixmap)})
        )

        # TARGET
        self.image_variant.grp_targets.target_added.connect(self.image_editor.add_target)
        self.image_variant.grp_targets.target_removed.connect(self.image_editor.remove_target)
        self.image_variant.grp_targets.target_removed.connect(self.element_manager.remove_target)
        self.image_editor.target_added.connect(self.element_manager.add_target)
        self.image_editor.target_added.connect(self.image_variant.grp_targets.add_target)
        self.image_editor.target_moved.connect(self.image_variant.grp_targets.update_target)
        self.image_variant.grp_targets.target_hovered.connect(self.image_editor.highlight_target)
        self.image_editor.target_hovered.connect(self.image_variant.grp_targets.highlight_target)
        self.image_editor.target_removed.connect(self.image_variant.grp_targets.remove_target)
        self.image_editor.target_removed.connect(self.element_manager.remove_target)

        # MATCH AREA
        self.image_variant.grp_properties.match_area_requested.connect(
            lambda area: self.image_editor.edit_match_area(area=area)
        )
        self.image_editor.match_area_defined.connect(
            lambda area: self.element_manager.update_variant({"match_area": area})
        )
        self.image_editor.match_area_defined.connect(
            lambda area: self.image_variant.grp_properties.update_match_area_label(area)
        )
        self.image_editor.match_area_removed.connect(
            lambda: self.image_variant.grp_properties.update_match_area_label(None)
        )
        self.image_variant.grp_properties.match_area_cleared.connect(self.image_editor.remove_match_area)
        self.image_variant.grp_properties.match_area_cleared.connect(
            lambda: self.element_manager.update_variant({"match_area": UNDEFINED})
        )
        self.image_editor.match_area_removed.connect(
            lambda: self.element_manager.update_variant({"match_area": UNDEFINED})
        )

    def _load_settings(self):
        """Restores window geometry and state from registry/config file."""
        settings = QSettings("Guimauve", "ElementEditor")
        geometry = settings.value("geometry")

        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 800)

        state = settings.value("windowState")
        if state:
            self.restoreState(state)

    def _save_settings(self):
        """Saves current window geometry and state."""
        settings = QSettings("Guimauve", "ElementEditor")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
