"""Panel beside a rectangle edited on the image: a warning, Cancel and the button applying it."""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from guimauve.gui.element_editor_next.components import Button, CenteredLabel, IconLabel, Variant
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

GAP = 8
"""Space between the rectangle and the panel."""


class RegionPanel(QFrame):
    """Floats under the rectangle, or above it without room, aligned on its right edge and kept in the view."""

    applied = Signal()
    cancelled = Signal()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("regionPanel")
        self.warning_icon = IconLabel(Icon.TRIANGLE_ALERT, theme, "warning")
        self.warning = CenteredLabel()
        self.warning.setProperty("message", "warning")
        self.cancel = Button("Cancel")
        self.cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel.clicked.connect(self.cancelled)
        self.apply = Button("Apply", Variant.PRIMARY)
        self.apply.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.apply.clicked.connect(self.applied)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(*[METRICS.space(1) + 2] * 4)
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(self.warning_icon)
        layout.addWidget(self.warning)
        layout.addSpacing(METRICS.space(1))
        layout.addWidget(self.cancel)
        layout.addWidget(self.apply)
        self.show_warning(None)
        self.hide()

    def set_action(self, text: str) -> None:
        self.apply.setText(text)
        self.adjustSize()

    def show_warning(self, text: str | None) -> None:
        self.warning.setText(text or "")
        self.warning.setVisible(text is not None)
        self.warning_icon.setVisible(text is not None)
        self.adjustSize()

    def place(self, rect: QRectF) -> None:
        """Places the panel by a rectangle of the view, in coordinates of its parent."""
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        width, height = self.width(), self.height()
        x = rect.right() - width
        y = rect.bottom() + GAP
        if y + height > parent.height() - GAP:
            y = rect.top() - GAP - height
        x = min(max(x, GAP), parent.width() - width - GAP)
        y = min(max(y, GAP), parent.height() - height - GAP)
        self.move(round(x), round(y))
