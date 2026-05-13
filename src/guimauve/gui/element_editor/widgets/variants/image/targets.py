from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from guimauve.gui.element_editor.icons import icons
from guimauve.models.variant import Target


class TargetItem(QWidget):
    hover_changed = Signal(object, bool)

    def __init__(self, target, parent=None):
        super().__init__(parent)
        self.target = target

        self._init_ui()
        self._init_signals()

        self.edt_name.setStyleSheet("border: 2px solid transparent;")

    def refresh(self):
        self.lbl_coords.setText(f"({self.target.x}, {self.target.y})")

    def set_highlight(self, active):
        if active:
            self.edt_name.setStyleSheet("""
                background-color: rgba(255, 68, 68, 15);
                border: 2px solid #FF4444;
                border-radius: 4px;
            """)
        else:
            self.edt_name.setStyleSheet("border: 2px solid transparent;")

    def enterEvent(self, event):
        self.hover_changed.emit(self.target, True)
        self.set_highlight(True)

    def leaveEvent(self, event):
        self.hover_changed.emit(self.target, False)
        self.set_highlight(False)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self.edt_name = QLineEdit(self.target.name)

        self.lbl_coords = QLabel()
        self.refresh()

        self.btn_remove = QPushButton()
        self.btn_remove.setIcon(icons.REMOVE)

        layout.addWidget(self.edt_name)
        layout.addWidget(self.lbl_coords)
        layout.addWidget(self.btn_remove)

    def _init_signals(self):
        self.edt_name.textChanged.connect(lambda t: setattr(self.target, "name", t))


class TargetsGroup(QGroupBox):
    target_added = Signal(object)
    target_removed = Signal(object)
    target_hovered = Signal(object, bool)

    def __init__(self, parent=None):
        super().__init__("TARGETS", parent)
        self._widgets: dict[Target, TargetItem] = {}
        self._init_ui()

    def load(self, variant):
        self.clear()
        if not variant.targets:
            return

        for target in variant.targets:
            self.add_target(target)

    def clear(self):
        widgets = list(self._widgets.values())
        for widget in widgets:
            self.list_layout.removeWidget(widget)
            widget.deleteLater()
        self._widgets = {}

    def add_target(self, target):
        widget = TargetItem(target)

        self.list_layout.insertWidget(self.list_layout.count() - 1, widget)
        self._widgets[target] = widget

        self.target_added.emit(target)
        widget.hover_changed.connect(self.target_hovered)
        widget.btn_remove.clicked.connect(lambda: self.remove_target(target))

    def update_target(self, target):
        self._widgets[target].refresh()

    def remove_target(self, target):
        if widget := self._widgets.pop(target):
            self.target_removed.emit(target)
            self.list_layout.removeWidget(widget)
            widget.deleteLater()

    def highlight_target(self, target, active):
        if widget := self._widgets.get(target):
            widget.set_highlight(active)

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        self.list_layout.addStretch()

        self.scroll.setWidget(self.container)
        self.main_layout.addWidget(self.scroll)
