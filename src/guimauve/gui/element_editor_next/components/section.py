"""Collapsible section of the inspector."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from guimauve.gui.element_editor_next.components.badge import Badge, Count, CountBadge
from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager


class Section(QFrame):
    """Titled group of fields, collapsed when shown; only the user opens or collapses it.

    Badges on the header tell what is inside: values set, values set in the code, errors and warnings. Opening
    from elsewhere (set_open) is for an explicit request, such as a click on an issue.
    """

    def __init__(self, title: str, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("section", True)

        self._header = QPushButton(self)
        self._header.setObjectName("header")
        self._header.setProperty("sectionHeader", True)
        self._header.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._header.clicked.connect(lambda: self.set_open(not self.is_open()))
        self._chevron = IconLabel(Icon.CHEVRON_RIGHT, theme)
        self._title = QLabel(title)
        self._title.setProperty("sectionTitle", True)
        self._own = Badge()
        self._own.setToolTip("Values set here")
        self._code = CountBadge(Count.CODE, theme)
        self._code.setToolTip("Values set in the code for this call")
        self._errors = CountBadge(Count.ERROR, theme)
        self._warnings = CountBadge(Count.WARNING, theme)

        header = QHBoxLayout(self._header)
        header.setContentsMargins(METRICS.space(1), 0, METRICS.space(2), 0)
        header.setSpacing(METRICS.space(2))
        for widget in (self._chevron, self._title, self._own, self._code, self._errors, self._warnings):
            header.addWidget(widget)
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header.addStretch()

        self._body = QWidget(self)
        self._content = QVBoxLayout(self._body)
        self._content.setContentsMargins(METRICS.space(2), 0, METRICS.space(2), METRICS.space(3))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, METRICS.space(1), 0, METRICS.space(1))
        layout.setSpacing(METRICS.space(1))
        layout.addWidget(self._header)
        layout.addWidget(self._body)

        self.set_counts()
        self.set_open(False)

    def set_content(self, widget: QWidget) -> None:
        self._content.addWidget(widget)

    def set_counts(self, own: int = 0, code: int = 0, errors: int = 0, warnings: int = 0) -> None:
        """Numbers shown on the badges of the header; a badge at 0 is hidden."""
        self._own.setText(str(own))
        self._own.setVisible(own > 0)
        self._code.set_count(code)
        self._errors.set_count(errors)
        self._warnings.set_count(warnings)

    def is_open(self) -> bool:
        return not self._body.isHidden()

    def set_open(self, open_: bool) -> None:
        self._body.setVisible(open_)
        self._chevron.set_icon(Icon.CHEVRON_DOWN if open_ else Icon.CHEVRON_RIGHT)
