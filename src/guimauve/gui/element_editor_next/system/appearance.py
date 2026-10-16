"""Appearance settings of the system: color scheme and fonts."""

import sys
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


def is_dark_scheme() -> bool:
    """Whether the system uses a dark color scheme; False when unknown."""
    return QGuiApplication.styleHints().colorScheme() is Qt.ColorScheme.Dark


def watch_scheme(callback: Callable[[], None]) -> None:
    """Calls callback whenever the system color scheme changes."""
    QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _: callback())


def fallback_fonts() -> list[str]:
    """Fonts used when a character or the whole theme font is missing, in order."""
    if sys.platform == "win32":
        return ["Segoe UI"]
    return ["Noto Sans", "DejaVu Sans"]
