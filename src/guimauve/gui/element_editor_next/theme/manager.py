"""Theme chosen by the user, applied to the whole application."""

from enum import Enum

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from guimauve.gui.element_editor_next.system import fallback_fonts, is_dark_scheme, watch_scheme
from guimauve.gui.element_editor_next.theme.fonts import load_fonts
from guimauve.gui.element_editor_next.theme.icons import Icon, icon
from guimauve.gui.element_editor_next.theme.style import qpalette, stylesheet
from guimauve.gui.element_editor_next.theme.tokens import DARK, LIGHT, TYPE, Palette


class ThemeChoice(Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ThemeManager(QObject):
    """Applies the theme to the application and follows the system when the choice is System.

    Passed to the panels like the store; widgets that paint themselves or show icons update on changed.

    :param app: Application to style.
    :param settings: Where the choice of the user is kept.
    """

    changed = Signal()
    """The effective theme changed, from light to dark or back."""

    _KEY = "theme"

    def __init__(self, app: QApplication, settings: QSettings, parent: QObject | None = None):
        super().__init__(parent)
        self._app = app
        self._settings = settings
        self._choice = self._read_choice()
        self._dark = self._resolve_dark()

    def apply(self) -> None:
        """Styles the application; call once, after the QApplication is created."""
        load_fonts()
        font = QFont()
        font.setFamilies([TYPE.family, *fallback_fonts()])
        font.setPixelSize(TYPE.body)
        self._app.setFont(font)
        self._app.setStyle("Fusion")
        watch_scheme(self._refresh)
        self._style()

    @property
    def choice(self) -> ThemeChoice:
        return self._choice

    def set_choice(self, choice: ThemeChoice) -> None:
        """Changes the choice and keeps it for the next sessions."""
        self._choice = choice
        self._settings.setValue(self._KEY, choice.value)
        self._refresh()

    @property
    def is_dark(self) -> bool:
        return self._dark

    @property
    def palette(self) -> Palette:
        return DARK if self._dark else LIGHT

    def icon(self, name: Icon, role: str = "text_secondary") -> QIcon:
        """Icon drawn in a color of the palette, by role name, and in the muted text color when disabled."""
        return icon(name, getattr(self.palette, role), self.palette.text_muted)

    def _read_choice(self) -> ThemeChoice:
        try:
            return ThemeChoice(self._settings.value(self._KEY, ThemeChoice.SYSTEM.value))
        except ValueError:
            return ThemeChoice.SYSTEM

    def _resolve_dark(self) -> bool:
        if self._choice is ThemeChoice.SYSTEM:
            return is_dark_scheme()
        return self._choice is ThemeChoice.DARK

    def _refresh(self) -> None:
        dark = self._resolve_dark()
        if dark != self._dark:
            self._dark = dark
            self._style()
            self.changed.emit()

    def _style(self) -> None:
        self._app.setPalette(qpalette(self.palette))
        self._app.setStyleSheet(stylesheet(self.palette))
