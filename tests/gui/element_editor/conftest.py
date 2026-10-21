import os

# Widgets are tested without showing any window; set before pytest-qt creates the QApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402

from guimauve.gui.element_editor_next.theme import ThemeManager  # noqa: E402
from guimauve.gui.element_editor_next.theme import manager as manager_module  # noqa: E402


@pytest.fixture
def theme(qapp, tmp_path, monkeypatch):
    """Theme manager on a light system, with its own settings file; the application is left unstyled."""
    monkeypatch.setattr(manager_module, "is_dark_scheme", lambda: False)
    return ThemeManager(qapp, QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
