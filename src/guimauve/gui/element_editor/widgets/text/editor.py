from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QVBoxLayout, QWidget
from sugar import UNDEFINED

from guimauve.gui.element_editor.widgets.text.toolbar.toolbar import TextToolbar


class TextEditor(QWidget):
    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._init_signals()

    def load(self, variant):
        self.blockSignals(True)
        text = variant.text
        self.edt_text.setText(text if text not in (None, UNDEFINED) else "")
        self._resize_to_content()
        self.blockSignals(False)

    def _on_changed(self):
        self._resize_to_content()
        self.changed.emit({"text": self.edt_text.text()})

    def _resize_to_content(self):
        text = self.edt_text.text() or self.edt_text.placeholderText()
        width = self.edt_text.fontMetrics().horizontalAdvance(text) + 40
        self.edt_text.setFixedWidth(max(width, 200))

    def _init_ui(self):
        self.toolbar = TextToolbar()

        self.edt_text = QLineEdit()
        self.edt_text.setPlaceholderText("Text to search for...")
        self.edt_text.setFrame(False)
        self.edt_text.setAlignment(Qt.AlignCenter)
        self.edt_text.setStyleSheet("background: transparent; border: none;")

        font = self.edt_text.font()
        font.setPointSize(24)
        self.edt_text.setFont(font)

        self._resize_to_content()

        centered_layout = QHBoxLayout()
        centered_layout.addStretch()
        centered_layout.addWidget(self.edt_text)
        centered_layout.addStretch()

        content_layout = QVBoxLayout()
        content_layout.addStretch()
        content_layout.addLayout(centered_layout)
        content_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toolbar)
        layout.addLayout(content_layout)

    def _init_signals(self):
        self.edt_text.textChanged.connect(self._on_changed)
