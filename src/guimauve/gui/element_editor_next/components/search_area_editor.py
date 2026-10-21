"""Editor of the search area: a part of the screen, or a custom area."""

from typing import Any

from guimauve.enums import ScreenArea
from guimauve.gui.element_editor_next.components.editors import SEPARATOR, ComboEditor, Option, describe, label_of
from guimauve.models.area import Area

_GROUPS = (
    (ScreenArea.FULL,),
    (ScreenArea.LEFT, ScreenArea.TOP, ScreenArea.RIGHT, ScreenArea.BOTTOM),
    (ScreenArea.TOP_LEFT, ScreenArea.TOP_RIGHT, ScreenArea.BOTTOM_RIGHT, ScreenArea.BOTTOM_LEFT),
    (ScreenArea.COL_1, ScreenArea.COL_2, ScreenArea.COL_3),
    (ScreenArea.ROW_1, ScreenArea.ROW_2, ScreenArea.ROW_3),
)


class SearchAreaEditor(ComboEditor):
    """The parts of the screen by group; a custom area keeps its own entry, with its coordinates in the tooltip.

    Drawing a new custom area comes with the capture interface.
    """

    def options(self, value: Any) -> list[Option | object]:
        options: list[Option | object] = []
        for group in _GROUPS:
            if options:
                options.append(SEPARATOR)
            options += [Option(area, label_of(area)) for area in group]
        if isinstance(value, Area):
            options += [SEPARATOR, Option(value, f"Custom, {value.width} × {value.height}", describe(value))]
        return options
