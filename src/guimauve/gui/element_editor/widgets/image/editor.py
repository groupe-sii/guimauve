from PySide6.QtCore import QRect, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QWidget

from guimauve.gui.element_editor.widgets.image.status_bar import StatusBar
from guimauve.gui.element_editor.widgets.image.toolbar.toolbar import ImageToolbar
from guimauve.gui.element_editor.widgets.image.viewer.floating_toolbar import FloatingToolbar
from guimauve.gui.element_editor.widgets.image.viewer.target_point import TargetPointItem
from guimauve.gui.element_editor.widgets.image.viewer.viewer import ImageViewer
from guimauve.models.area import Area
from guimauve.models.variant import Target


class ImageEditor(QWidget):
    captured_image_loaded = Signal(object)
    crop_applied = Signal(object)
    target_added = Signal(object)
    target_moved = Signal(object)
    target_hovered = Signal(object, bool)
    target_removed = Signal(object)
    match_area_defined = Signal(object)
    match_area_removed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()
        self._init_signals()

        self.target_items: dict[Target, TargetPointItem] = {}
        self._edit_mode = None

    def load_image(self, pixmap):
        self.remove_image()
        self.viewer.set_image(pixmap)
        self.status_bar.update_image_size(pixmap.width(), pixmap.height())

    def load_captured_image(self, pixmap):
        self.load_image(pixmap)
        self.remove_match_area()
        self.remove_targets()
        self.captured_image_loaded.emit(pixmap)

    def remove_image(self):
        self.viewer.remove_image()

    def remove_targets(self):
        for target in list(self.target_items):
            self.remove_target(target)
            self.target_removed.emit(target)

    def apply_crop(self):
        if pixmap := self.viewer.apply_crop():
            self.remove_match_area()
            self.remove_targets()
            self.status_bar.update_image_size(pixmap.width(), pixmap.height())
            self.crop_applied.emit(pixmap)
        self.cancel_crop()

    def cancel_crop(self):
        self.viewer.set_crop_visible(False)
        self.floating_toolbar.hide()
        if self.viewer.match_area_item:
            self.viewer.set_match_area_visible(True)
            self.viewer.match_area_item.set_editable(False)
        self.set_target_visible(True)
        self.toolbar.setEnabled(True)

    def edit_match_area(self, area=None):
        if not self.viewer.has_image:
            return

        if area:
            rect = QRect(*area.as_xywh())
            self.viewer.set_match_area_visible(True, rect=rect)
            return

        self._edit_mode = "match"

        self.floating_toolbar.btn_cancel.setVisible(False)

        self.toolbar.setEnabled(False)
        self.set_target_visible(False)
        self.viewer.block_targets = True
        self.viewer.set_match_area_visible(True)
        self.refresh_floating_toolbar()

    def validate_match_area(self):
        rect = self.viewer.get_match_area_rect()
        self.viewer.match_area_item.set_editable(False)

        top = int(rect.top())
        right = int(rect.right())
        bottom = int(rect.bottom())
        left = int(rect.left())
        area = Area(top=top, right=right, bottom=bottom, left=left)

        self.match_area_defined.emit(area)

    def remove_match_area(self):
        self.viewer.remove_match_area()
        self.match_area_removed.emit()

    def refresh_floating_toolbar(self):
        mapping = {"crop": self.viewer.crop_item, "match": self.viewer.match_area_item}

        active_item = mapping.get(self._edit_mode)

        if active_item:
            scene_rect = active_item.mapToScene(active_item.rect()).boundingRect()
            view_rect = self.viewer.mapFromScene(scene_rect).boundingRect()

            self.floating_toolbar.anchor_to(view_rect)
            self.floating_toolbar.show()
        else:
            self.floating_toolbar.hide()

    def add_target(self, target):
        if target in self.target_items:
            return

        item = TargetPointItem(target)
        item.position_changed.connect(self.target_moved)
        item.hover_changed.connect(self.target_hovered)
        self.viewer.scene().addItem(item)
        self.target_items[target] = item

    def remove_target(self, target):
        item = self.target_items.pop(target, None)
        if item:
            self.viewer.scene().removeItem(item)
            item.deleteLater()

    def clear_targets(self):
        for target_item in self.target_items.values():
            self.viewer.scene().removeItem(target_item)
            target_item.deleteLater()
        self.target_items = {}

    def set_target_visible(self, visible):
        self.viewer.setUpdatesEnabled(False)
        try:
            for item in self.target_items.values():
                item.setVisible(visible)
        finally:
            self.viewer.setUpdatesEnabled(True)
            self.viewer.viewport().update()

    def highlight_target(self, target, active):
        if item := self.target_items.get(target):
            item.is_hovered = active
            item.update()

    def _on_point_clicked(self, point):
        if not self.viewer.has_image:
            return

        x = int(point.x())
        y = int(point.y())
        target = Target(name="", x=x, y=y)
        self.add_target(target)
        self.target_added.emit(target)

    def _on_import_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
        )

        if not file_path:
            return

        pixmap = QPixmap(file_path)

        if pixmap.isNull():
            QMessageBox.critical(
                self, "Import Error", f"Unable to load image: {file_path}\nFormat might not be supported."
            )
            return

        self.load_captured_image(pixmap)

    def _on_crop_clicked(self):
        if not self.viewer.has_image:
            return

        self._edit_mode = "crop"

        self.floating_toolbar.btn_cancel.setVisible(True)

        self.toolbar.setEnabled(False)
        self.set_target_visible(False)
        self.viewer.block_targets = True
        self.viewer.set_match_area_visible(False)
        self.viewer.set_crop_visible(True)
        self.refresh_floating_toolbar()

    def _on_floating_apply(self):
        if self._edit_mode == "crop":
            self.apply_crop()
        elif self._edit_mode == "match":
            self.validate_match_area()

        self._end_edit_mode()

    def _on_floating_cancel(self):
        if self._edit_mode == "crop":
            self.cancel_crop()
        elif self._edit_mode == "match":
            self.viewer.set_match_area_visible(False)

        self._end_edit_mode()

    def _on_mouse_moved(self, scene_pos):
        if pixmap_item := self.viewer.pixmap_item:
            local_pos = pixmap_item.mapFromScene(scene_pos)
            self.status_bar.update_mouse_pos(local_pos.x(), local_pos.y())

    def _end_edit_mode(self):
        self.floating_toolbar.hide()
        self.set_target_visible(True)
        self.viewer.block_targets = False
        self.toolbar.setEnabled(True)
        self._edit_mode = None

    def _init_ui(self):
        # TOOLBAR
        self.toolbar = ImageToolbar()

        # VIEWER
        self.viewer = ImageViewer(self)
        self.floating_toolbar = FloatingToolbar(self.viewer)

        # STATUS BAR
        self.status_bar = StatusBar()

        # ASSEMBLY
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.viewer)
        layout.addWidget(self.status_bar)

    def _init_signals(self):
        # TOOLBAR
        self.toolbar.btn_capture.image_ready.connect(self.load_captured_image)
        self.toolbar.btn_import.clicked.connect(self._on_import_clicked)
        self.toolbar.btn_crop.clicked.connect(self._on_crop_clicked)

        # CROP TOOLBAR
        self.viewer.crop_changed.connect(self.refresh_floating_toolbar)
        self.viewer.view_changed.connect(self.refresh_floating_toolbar)
        self.floating_toolbar.btn_apply.clicked.connect(self._on_floating_apply)
        self.floating_toolbar.btn_cancel.clicked.connect(self._on_floating_cancel)

        # TARGET
        self.viewer.point_clicked.connect(self._on_point_clicked)

        # STATUS BAR
        self.viewer.view_changed.connect(self.status_bar.update_zoom)
        self.viewer.mouse_moved.connect(self._on_mouse_moved)
