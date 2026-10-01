"""Themed icon loader with lazy caching.

Each icon is loaded on first access via ``get_themed_icon``, then
served from a class-level cache for the rest of the process.
"""

from pathlib import Path

from PySide6.QtGui import QIcon

from guimauve.gui.common.resources import get_themed_icon

ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"


class IconManager:
    """Exposes application icons as attributes, loading them lazily."""

    _cache: dict[str, QIcon] = {}

    def _get_cached(self, name: str) -> QIcon:
        if name not in self._cache:
            self._cache[name] = get_themed_icon(name, ICONS_DIR)
        return self._cache[name]

    @property
    def PLAY(self) -> QIcon:
        return self._get_cached("play")

    @property
    def PAUSE(self) -> QIcon:
        return self._get_cached("pause")

    @property
    def RESET(self) -> QIcon:
        return self._get_cached("reset")

    @property
    def EDIT(self) -> QIcon:
        return self._get_cached("edit")

    @property
    def OPEN(self) -> QIcon:
        return self._get_cached("open")

    @property
    def RECORD(self) -> QIcon:
        return self._get_cached("record")

    @property
    def REPLAY(self) -> QIcon:
        return self._get_cached("replay")

    @property
    def SAVE(self) -> QIcon:
        return self._get_cached("save")

    @property
    def BACKGROUND(self) -> QIcon:
        return self._get_cached("background")


icons = IconManager()
