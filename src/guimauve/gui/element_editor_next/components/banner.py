"""Message shown above a panel or the window."""

from enum import StrEnum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from guimauve.gui.element_editor_next.components.buttons import IconButton
from guimauve.gui.element_editor_next.components.icon_label import IconLabel
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager


class Tone(StrEnum):
    """Kind of message, read by the stylesheet; each one has its own icon, so color is never the only cue."""

    NEUTRAL = "neutral"
    INHERIT = "inherit"
    WARNING = "warning"
    ERROR = "error"


_ICONS = {
    Tone.NEUTRAL: (Icon.INFO, "text_secondary"),
    Tone.INHERIT: (Icon.INFO, "inherit"),
    Tone.WARNING: (Icon.TRIANGLE_ALERT, "warning"),
    Tone.ERROR: (Icon.CIRCLE_ALERT, "error"),
}


class Banner(QFrame):
    """Icon, text with optional links, actions on the right and an optional close button.

    :param strip: Full width with a bottom border, for the top of the window; a rounded card otherwise.
    """

    link_activated = Signal(str)
    """A link of the text was clicked; its href is given."""

    closed = Signal()
    """The user closed the banner, which is now hidden."""

    def __init__(
        self,
        text: str,
        tone: Tone,
        theme: ThemeManager,
        strip: bool = False,
        closable: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setProperty("banner", tone.value)
        self.setProperty("strip", strip)

        self._text = QLabel(text)
        self._text.setObjectName("text")
        self._text.setWordWrap(True)
        self._text.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        self._text.linkActivated.connect(self.link_activated)

        self._actions = QHBoxLayout()
        self._actions.setSpacing(METRICS.space(2))

        name, role = _ICONS[tone]
        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(3), METRICS.space(2), METRICS.space(2), METRICS.space(2))
        layout.setSpacing(METRICS.space(2))
        layout.addWidget(IconLabel(name, theme, role), 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._text, 1)
        layout.addLayout(self._actions)

        if closable:
            close = IconButton(Icon.X, theme, "Close")
            close.setObjectName("close")
            close.clicked.connect(self._close)
            layout.addWidget(close, 0, Qt.AlignmentFlag.AlignVCenter)

    def text(self) -> str:
        return self._text.text()

    def set_text(self, text: str) -> None:
        self._text.setText(text)

    def add_action(self, widget: QWidget) -> None:
        """Adds a button on the right of the text, before the close button."""
        self._actions.addWidget(widget)

    def _close(self) -> None:
        self.hide()
        self.closed.emit()
