"""Fonts embedded in the package."""

from functools import cache
from pathlib import Path

from PySide6.QtGui import QFontDatabase

from guimauve.gui.element_editor_next.theme.tokens import TYPE

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"


@cache
def load_fonts() -> bool:
    """Registers the embedded fonts with Qt, once, and returns whether the family of the theme is available.

    Needs a QGuiApplication. When it returns False, the fallback fonts of the system layer apply.
    """
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))
    return TYPE.family in QFontDatabase.families()
