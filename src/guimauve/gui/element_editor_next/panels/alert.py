"""Banner at the top of the window: why the editor opened."""

from html import escape

from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.components import Banner, Tone
from guimauve.gui.element_editor_next.theme import ThemeManager

MANUAL_CALL = "manual_call"
"""Action given by the controller when the editor is opened outside an action."""


def alert_text(message: str, action: str) -> str:
    """The message, then the action that was running, e.g. "Element not found, while running click()"."""
    text = escape(message)
    return f"{text}, while running {escape(action)}()" if action and action != MANUAL_CALL else text


class AlertBanner(Banner):
    """Why the editor opened, as Context.message and Context.action; hidden without a message, as from the CLI."""

    def __init__(self, message: str, action: str, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(alert_text(message, action), Tone.ERROR, theme, strip=True, closable=True, parent=parent)
        self.setVisible(bool(message))
