"""Collapsible section of the inspector."""

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components.badge import Badge
from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager


class Section(QFrame):
    """Titled group of fields, open or collapsed.

    It is open when it has an error; otherwise when the panel asks for it (set_auto_open), unless the user
    collapsed it. A manual collapse is kept in the settings; opening the section again by hand forgets it.

    :param key: Identifier of the section, used to keep its manual collapse.
    :param settings: Where the manual collapse is kept.
    """

    def __init__(self, key: str, title: str, theme: ThemeManager, settings: QSettings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("section", True)
        self._settings = settings
        self._setting = f"sections/{key}/collapsed"
        self._auto_open = False
        self._has_error = False

        self._header = QPushButton(self)
        self._header.setObjectName("header")
        self._header.setProperty("sectionHeader", True)
        self._header.clicked.connect(self._toggle)
        self._chevron = IconLabel(Icon.CHEVRON_RIGHT, theme)
        self._title = QLabel(title)
        self._title.setProperty("sectionTitle", True)
        self._badge = Badge()
        self._summary = QLabel()
        self._summary.setProperty("muted", True)

        header = QHBoxLayout(self._header)
        header.setContentsMargins(METRICS.space(1), 0, METRICS.space(2), 0)
        header.setSpacing(METRICS.space(2))
        for widget in (self._chevron, self._title, self._badge):
            header.addWidget(widget)
        header.addStretch()
        header.addWidget(self._summary)
        for widget in (self._chevron, self._title, self._badge, self._summary):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._body = QWidget(self)
        self._content = QVBoxLayout(self._body)
        self._content.setContentsMargins(METRICS.space(2), 0, METRICS.space(2), METRICS.space(3))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, METRICS.space(1), 0, METRICS.space(1))
        layout.setSpacing(METRICS.space(1))
        layout.addWidget(self._header)
        layout.addWidget(self._body)

        self.set_badge(0)
        self._show(self._should_open())

    def set_content(self, widget: QWidget) -> None:
        self._content.addWidget(widget)

    def set_summary(self, text: str) -> None:
        """Short description shown while collapsed, such as "Not set" or "Sort: confidence"."""
        self._summary.setText(text)
        self._show(self.is_open())

    def set_badge(self, count: int) -> None:
        """Number of values overridden in the section; hidden at 0."""
        self._badge.setText(str(count))
        self._badge.setVisible(count > 0)

    def set_auto_open(self, auto_open: bool, has_error: bool = False) -> None:
        """Opens or collapses the section by its content, as decided by the panel."""
        self._auto_open, self._has_error = auto_open, has_error
        self._show(self._should_open())

    def is_open(self) -> bool:
        return not self._body.isHidden()

    def _should_open(self) -> bool:
        collapsed = self._settings.value(self._setting, False, type=bool)
        return self._has_error or (self._auto_open and not collapsed)

    def _toggle(self) -> None:
        if self.is_open():
            self._settings.setValue(self._setting, True)
        else:
            self._settings.remove(self._setting)
        self._show(not self.is_open())

    def _show(self, open_: bool) -> None:
        self._body.setVisible(open_)
        self._summary.setVisible(not open_ and bool(self._summary.text()))
        self._chevron.set_icon(Icon.CHEVRON_DOWN if open_ else Icon.CHEVRON_RIGHT)
