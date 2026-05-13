from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
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

        self.name = None

    def load(self, element):
        self.name = element.name
        for variant in element.variants or []:
            self.add_variant(variant)
        self.lst_variants.setCurrentRow(0)

    def add_variant(self, variant):
        prefix = "[IMG]" if isinstance(variant, ImageVariant) else "[TXT]"
        item = QListWidgetItem(f"{prefix} {variant.name}")
        item.setData(Qt.UserRole, variant)
        self.lst_variants.addItem(item)
        self.lst_variants.setCurrentItem(item)

    def _on_add(self, variant_type):
        name, ok = QInputDialog.getText(self, f"New {variant_type} variant", "Choose a name:", text=self.name)
        if ok and name.strip():
            if variant_type == "IMAGE":
                new_var = ImageVariant(name=name.strip())
            else:
                new_var = TextVariant(name=name.strip())

            self.variant_added.emit(new_var)
            self.add_variant(new_var)

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
            new_order_variants.append(item.data(Qt.UserRole))

        self.variants_order_changed.emit(new_order_variants)

    def _init_ui(self):
        # TOOLBAR
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(2)

        icon_size = QSize(20, 20)

        # ADD IMAGE
        self.btn_add_img = QToolButton()
        self.btn_add_img.setIcon(icons.ADD_IMAGE)
        self.btn_add_img.setIconSize(icon_size)
        self.btn_add_img.setToolTip("Add Image")
        self.btn_add_img.setAutoRaise(True)

        # ADD TEXT
        self.btn_add_text = QToolButton()
        self.btn_add_text.setIcon(icons.ADD_TEXT)
        self.btn_add_text.setIconSize(icon_size)
        self.btn_add_text.setToolTip("Add Text")
        self.btn_add_text.setAutoRaise(True)
        self.btn_add_text.setVisible(False)

        # DELETE
        self.btn_delete = QToolButton()
        self.btn_delete.setIcon(icons.DELETE)
        self.btn_delete.setIconSize(icon_size)
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

        # ASSEMBLY
        layout = QVBoxLayout(self)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.lst_variants)

    def _init_signals(self):
        self.btn_add_img.clicked.connect(lambda: self._on_add("IMAGE"))
        self.btn_add_text.clicked.connect(lambda: self._on_add("TEXT"))
        self.btn_delete.clicked.connect(self._on_remove)
        self.lst_variants.currentItemChanged.connect(self._on_selection_changed)
        self.lst_variants.model().rowsMoved.connect(self._on_rows_moved)
