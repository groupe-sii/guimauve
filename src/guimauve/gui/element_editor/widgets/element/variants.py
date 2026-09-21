from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
)

from guimauve.gui.element_editor.icons import icons
from guimauve.models.variant import ImageVariant, TextVariant


class VariantsGroup(QGroupBox):
    variant_added = Signal(object)
    variant_selected = Signal(object)
    variant_renamed = Signal(str)
    variant_removed = Signal(object, object)
    variants_order_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__("VARIANTS", parent)
        self._init_ui()
        self._init_signals()

        # Persist highlight visibility even if focus is lost in the variants list
        palette = self.lst_variants.palette()
        highlight_color = palette.color(QPalette.Active, QPalette.Highlight)
        palette.setColor(QPalette.Inactive, QPalette.Highlight, highlight_color)
        highlight_text = palette.color(QPalette.Active, QPalette.HighlightedText)
        palette.setColor(QPalette.Inactive, QPalette.HighlightedText, highlight_text)

        self.lst_variants.setPalette(palette)

    def load(self, element):
        for variant in element.variants or []:
            self.add_variant(variant)
        self.lst_variants.setCurrentRow(0)

    def add_variant(self, variant):
        icon = icons.IMAGE if isinstance(variant, ImageVariant) else icons.TEXT
        item = QListWidgetItem(icon, variant.name)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setData(Qt.UserRole, variant)
        self.lst_variants.addItem(item)
        self.lst_variants.setCurrentItem(item)

    def _next_variant_name(self):
        existing = set()
        for i in range(self.lst_variants.count()):
            variant = self.lst_variants.item(i).data(Qt.UserRole)
            existing.add(variant.name)

        if "DEFAULT" not in existing:
            return "DEFAULT"

        i = 1
        while f"VARIANT_{i}" in existing:
            i += 1
        return f"VARIANT_{i}"

    def _on_add(self, variant_type):
        name = self._next_variant_name()
        if variant_type == "IMAGE":
            new_var = ImageVariant(name=name)
        else:
            new_var = TextVariant(name=name)

        self.variant_added.emit(new_var)
        self.add_variant(new_var)

    def _on_item_renamed(self, item):
        variant = item.data(Qt.UserRole)
        old_name = variant.name
        new_name = item.text().strip().upper().replace(" ", "_")

        taken = False
        for i in range(self.lst_variants.count()):
            other = self.lst_variants.item(i)
            if other is not item and other.data(Qt.UserRole).name == new_name:
                taken = True
                break

        final = old_name if (not new_name or taken) else new_name

        if item.text() != final:
            self.lst_variants.blockSignals(True)
            item.setText(final)
            self.lst_variants.blockSignals(False)

        if final != old_name:
            self.variant_renamed.emit(final)

        self.lst_variants.blockSignals(True)
        item.setText(final)
        self.lst_variants.blockSignals(False)

    def _on_remove(self):
        current_item = self.lst_variants.currentItem()
        if not current_item:
            return

        row = self.lst_variants.row(current_item)
        variant_to_remove = current_item.data(Qt.UserRole)

        confirm = QMessageBox.question(
            self, "Remove variant", f"Remove the variant '{variant_to_remove.name}'?", QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            next_variant = None

            if self.lst_variants.count() > 1:
                next_row = row - 1 if row == self.lst_variants.count() - 1 else row + 1
                next_item = self.lst_variants.item(next_row)
                if next_item:
                    next_variant = next_item.data(Qt.UserRole)

            self.variant_removed.emit(variant_to_remove, next_variant)
            self.lst_variants.takeItem(row)

            if next_variant:
                self.lst_variants.setCurrentRow(max(0, row - 1) if row == self.lst_variants.count() else row)

    def _on_selection_changed(self, current, previous):
        if not current:
            return

        variant = current.data(Qt.UserRole)
        self.variant_selected.emit(variant)

    def _on_rows_moved(self, parent, start, end, destination, dest_row):
        new_order_variants = []
        for i in range(self.lst_variants.count()):
            item = self.lst_variants.item(i)
            variant = item.data(Qt.UserRole)
            new_order_variants.append(variant)

        self.variants_order_changed.emit(new_order_variants)

    def _init_ui(self):
        # TOOLBAR
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(2)

        button_icon_size = QSize(20, 20)
        item_icon_size = QSize(16, 16)

        # ADD IMAGE
        self.btn_add_img = QToolButton()
        self.btn_add_img.setIcon(icons.ADD_IMAGE)
        self.btn_add_img.setIconSize(button_icon_size)
        self.btn_add_img.setToolTip("Add Image")
        self.btn_add_img.setAutoRaise(True)

        # ADD TEXT
        self.btn_add_text = QToolButton()
        self.btn_add_text.setIcon(icons.ADD_TEXT)
        self.btn_add_text.setIconSize(button_icon_size)
        self.btn_add_text.setToolTip("Add Text")
        self.btn_add_text.setAutoRaise(True)

        # DELETE
        self.btn_delete = QToolButton()
        self.btn_delete.setIcon(icons.DELETE)
        self.btn_delete.setIconSize(button_icon_size)
        self.btn_delete.setToolTip("Delete")
        self.btn_delete.setAutoRaise(True)

        buttons_layout.addWidget(self.btn_add_img)
        buttons_layout.addWidget(self.btn_add_text)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_delete)

        # VARIANTS LIST
        self.lst_variants = QListWidget()
        self.lst_variants.setDragEnabled(True)
        self.lst_variants.setAcceptDrops(True)
        self.lst_variants.setDragDropMode(QAbstractItemView.InternalMove)
        self.lst_variants.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lst_variants.setIconSize(item_icon_size)

        # ASSEMBLY
        layout = QVBoxLayout(self)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.lst_variants)

    def _init_signals(self):
        self.btn_add_img.clicked.connect(lambda: self._on_add("IMAGE"))
        self.btn_add_text.clicked.connect(lambda: self._on_add("TEXT"))
        self.btn_delete.clicked.connect(self._on_remove)
        self.lst_variants.itemChanged.connect(self._on_item_renamed)
        self.lst_variants.currentItemChanged.connect(self._on_selection_changed)
        self.lst_variants.model().rowsMoved.connect(self._on_rows_moved)
