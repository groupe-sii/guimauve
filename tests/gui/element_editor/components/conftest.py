import pytest
from PySide6.QtCore import QSettings

from guimauve.gui.element_editor_next.theme import ThemeManager
from guimauve.gui.element_editor_next.theme import manager as manager_module


@pytest.fixture
def theme(qapp, tmp_path, monkeypatch):
    """Theme manager on a light system, with its own settings file; the application is left unstyled."""
    monkeypatch.setattr(manager_module, "is_dark_scheme", lambda: False)
    return ThemeManager(qapp, QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))


@pytest.fixture
def color_at():
    """Color of the pixel at (x, y) of a rendered widget, as #RRGGBB."""

    def color(widget, x: int, y: int) -> str:
        return widget.grab().toImage().pixelColor(x, y).name().upper()

    return color
