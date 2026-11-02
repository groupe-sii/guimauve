"""Editor of the search area: a part of the screen, or a custom area."""

from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QComboBox, QWidget

from guimauve.enums import ScreenArea
from guimauve.gui.element_editor.components.area_grid import AreaGrid, GridEntry, mini_screen
from guimauve.gui.element_editor.components.buttons import text_icon_button
from guimauve.gui.element_editor.components.editors import (
    SEPARATOR,
    ComboEditor,
    Option,
    _ComboBox,
    describe,
    label_of,
)
from guimauve.gui.element_editor.theme import METRICS, Icon, ThemeManager
from guimauve.models.area import Area

DRAW = "Draw on screen"

_GROUPS = (
    (ScreenArea.FULL,),
    (ScreenArea.LEFT, ScreenArea.TOP, ScreenArea.RIGHT, ScreenArea.BOTTOM),
    (ScreenArea.TOP_LEFT, ScreenArea.TOP_RIGHT, ScreenArea.BOTTOM_RIGHT, ScreenArea.BOTTOM_LEFT),
    (ScreenArea.COL_1, ScreenArea.COL_2, ScreenArea.COL_3),
    (ScreenArea.ROW_1, ScreenArea.ROW_2, ScreenArea.ROW_3),
)


class _AreaCombo(_ComboBox):
    """List whose popup is the grid of the parts of the screen; the values are in the data of the items."""

    def __init__(self, theme: ThemeManager):
        super().__init__()
        self._theme = theme
        self.grid: AreaGrid | None = None

    def showPopup(self) -> None:
        entries = [
            GridEntry(
                index,
                self.itemData(index),
                self.itemText(index),
                self.itemData(index, Qt.ItemDataRole.ToolTipRole) or "",
            )
            for index in range(self.count())
            if self.itemData(index) is not None
        ]
        # parented to the window: a child of a list is painted by the stylesheet as its popup, without background
        self.grid = AreaGrid(entries, self.currentIndex(), self._theme, self.window())
        self.grid.chosen.connect(self._choose)
        self.grid.destroyed.connect(self._closed)
        self.grid.show_under(self)

    def hidePopup(self) -> None:
        if self.grid is not None:
            self.grid.close()

    def _choose(self, index: int) -> None:
        self.setCurrentIndex(index)
        self.activated.emit(index)

    def _closed(self) -> None:
        self.grid = None


class SearchAreaEditor(ComboEditor):
    """The parts of the screen by group, each with its mini screen; a custom area keeps its own entry, with its
    coordinates in the tooltip. The list opens as a grid of mini screens.

    A button under the list asks to draw a custom area on screen; it shows once set_draw says whether it can.
    """

    draw_requested = Signal()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        self._theme = theme  # read by _make_combo, which the base class calls
        super().__init__(parent)
        theme.changed.connect(self.refresh)  # the mini screens follow the theme
        self.draw = text_icon_button(DRAW, Icon.SQUARE_DASHED, theme)
        self.draw.setObjectName("drawSearchArea")
        self.draw.clicked.connect(self.draw_requested)
        self.draw.hide()
        self.add_below(self.draw)
        layout = self.layout()
        assert layout is not None
        layout.setAlignment(self.draw, Qt.AlignmentFlag.AlignLeft)

    def set_draw(self, unavailable: str | None) -> None:
        """Shows the button, disabled with the reason when nothing can be drawn."""
        self.draw.show()
        self.draw.setEnabled(unavailable is None)
        self.draw.setToolTip(unavailable or "")

    def refresh(self) -> None:
        super().refresh()
        size = QSize(METRICS.area_item_icon_width, METRICS.area_item_icon_height)
        self._combo.setIconSize(size)
        for index, option in enumerate(self._options):
            if isinstance(option, Option):
                self._combo.setItemData(index, option.value)
                if isinstance(option.value, ScreenArea):
                    self._combo.setItemIcon(index, mini_screen(option.value, size, self._theme))

    def _make_combo(self) -> QComboBox:
        return _AreaCombo(self._theme)

    def options(self, value: Any) -> list[Option | object]:
        options: list[Option | object] = []
        for group in _GROUPS:
            if options:
                options.append(SEPARATOR)
            options += [Option(area, label_of(area)) for area in group]
        if isinstance(value, Area):
            options += [SEPARATOR, Option(value, f"Custom, {value.width} × {value.height}", describe(value))]
        return options
