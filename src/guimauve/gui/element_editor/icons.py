from pathlib import Path

from guimauve.gui.common.resources import get_themed_icon

ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"


class IconManager:
    _cache = {}

    def _get_cached(self, name: str):
        if name not in self._cache:
            self._cache[name] = get_themed_icon(name, ICONS_DIR)
        return self._cache[name]

    @property
    def ADD_IMAGE(self):
        return self._get_cached("add_image")

    @property
    def ADD_TEXT(self):
        return self._get_cached("add_text")

    @property
    def CAPTURE(self):
        return self._get_cached("capture")

    @property
    def CROP(self):
        return self._get_cached("crop")

    @property
    def DELETE(self):
        return self._get_cached("delete")

    @property
    def EDIT(self):
        return self._get_cached("edit")

    @property
    def FOLDER(self):
        return self._get_cached("folder")

    @property
    def IMPORT(self):
        return self._get_cached("import")

    @property
    def INITIAL(self):
        return self._get_cached("initial")

    @property
    def INSTANT(self):
        return self._get_cached("instant")

    @property
    def REMOVE(self):
        return self._get_cached("remove")

    @property
    def SAVE(self):
        return self._get_cached("save")

    @property
    def SKIP(self):
        return self._get_cached("skip")

    @property
    def TEST(self):
        return self._get_cached("test")

    @property
    def TIMER(self):
        return self._get_cached("timer")

    @property
    def VIEW(self):
        return self._get_cached("view")

    @property
    def WINDOW_ICON(self):
        return self._get_cached("window_icon")


icons = IconManager()
