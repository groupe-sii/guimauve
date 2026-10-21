"""Collapsible group of settings inside a section, such as the advanced settings of feature matching."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager


class Disclosure(QFrame):
    """A discreet header, e.g. "Advanced, 9 settings", that shows or hides its settings; collapsed at first."""

    def __init__(self, title: str, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title

        self._header = QPushButton(self)
        self._header.setObjectName("header")
        self._header.setProperty("sectionHeader", True)
        self._header.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._header.clicked.connect(lambda: self.set_open(not self.is_open()))
        self._chevron = IconLabel(Icon.CHEVRON_RIGHT, theme)
        self._label = QLabel(title)
        self._label.setProperty("muted", True)

        header = QHBoxLayout(self._header)
        header.setContentsMargins(METRICS.space(1), 0, METRICS.space(2), 0)
        header.setSpacing(METRICS.space(2))
        for widget in (self._chevron, self._label):
            header.addWidget(widget)
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header.addStretch()

        self._body = QWidget(self)
        self._content = QVBoxLayout(self._body)
        self._content.setContentsMargins(0, 0, 0, 0)
        self._content.setSpacing(METRICS.space(2))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(self._header)
        layout.addWidget(self._body)
        self.set_count(0)
        self.set_open(False)

    def add(self, widget: QWidget) -> None:
        self._content.addWidget(widget)

    def set_count(self, count: int) -> None:
        """Number of settings in the group, shown after the title."""
        self._label.setText(f"{self._title}, {count} setting{'s' if count != 1 else ''}")

    def is_open(self) -> bool:
        return not self._body.isHidden()

    def set_open(self, open_: bool) -> None:
        self._body.setVisible(open_)
        self._chevron.set_icon(Icon.CHEVRON_DOWN if open_ else Icon.CHEVRON_RIGHT)
