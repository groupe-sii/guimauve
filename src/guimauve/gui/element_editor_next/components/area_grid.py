"""Parts of the screen drawn as mini screens, and the grid that offers them in a popup."""

from typing import Any, NamedTuple

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QStyle,
    QStyleOption,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from guimauve.enums import ScreenArea
from guimauve.gui.element_editor_next.theme import METRICS, ThemeManager
from guimauve.gui.element_editor_next.theme.menus import round_corners

GRID = (
    (ScreenArea.FULL,),
    (ScreenArea.LEFT, ScreenArea.TOP, ScreenArea.RIGHT, ScreenArea.BOTTOM),
    (ScreenArea.TOP_LEFT, ScreenArea.TOP_RIGHT, ScreenArea.BOTTOM_LEFT, ScreenArea.BOTTOM_RIGHT),
    (ScreenArea.COL_1, ScreenArea.COL_2, ScreenArea.COL_3),
    (ScreenArea.ROW_1, ScreenArea.ROW_2, ScreenArea.ROW_3),
)
"""Rows of the grid: the whole screen, the halves, the quarters as they sit on screen, the columns, the rows."""


def mini_screen(area: ScreenArea, size: QSize, theme: ThemeManager, chosen: bool = False, ratio: float = 2.0) -> QIcon:
    """A screen outlined with its part filled, in the accent colour when chosen.

    :param ratio: Pixel ratio of the drawing, so that it stays sharp on a scaled screen.
    """
    palette = theme.palette
    pixmap = QPixmap(round(size.width() * ratio), round(size.height() * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    screen = QRectF(0.5, 0.5, size.width() - 1, size.height() - 1)
    painter.setPen(QPen(QColor(palette.text_muted), 1))
    painter.setBrush(QColor(palette.surface))
    painter.drawRoundedRect(screen, 2, 2)
    left, top, right, bottom = area.value
    part = QRectF(
        QPointF(screen.left() + left * screen.width(), screen.top() + top * screen.height()),
        QPointF(screen.left() + right * screen.width(), screen.top() + bottom * screen.height()),
    ).adjusted(1.5, 1.5, -1.5, -1.5)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(palette.accent if chosen else palette.text_muted))
    painter.drawRoundedRect(part, 1.5, 1.5)
    painter.end()
    return QIcon(pixmap)


class GridEntry(NamedTuple):
    """An entry of the list the grid stands for: its position there, its value, its label and tooltip."""

    position: int
    value: Any
    label: str
    tooltip: str = ""


class AreaGrid(QFrame):
    """Popup offering the parts of the screen as mini screens, by row of the same kind, the chosen one outlined.

    The name of the part under the cursor, else of the chosen one, shows under the grid. Any other entry, such as a
    custom area, is a text button below. A click chooses and closes; Esc or a click outside only closes.

    :param entries: Entries of the list; those holding a part of the screen go in the grid.
    :param current: Position of the chosen entry, -1 for none.
    """

    chosen = Signal(int)
    """Position of the entry chosen."""

    def __init__(self, entries: list[GridEntry], current: int, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("areaGrid")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        round_corners(self)
        self._names: dict[QObject, str] = {}
        by_value = {entry.value: entry for entry in entries if isinstance(entry.value, ScreenArea)}
        current_label = next((entry.label for entry in entries if entry.position == current), "")

        group = QButtonGroup(self)
        cells = QGridLayout()
        cells.setSpacing(METRICS.space(1) // 2)
        icon = QSize(METRICS.area_icon_width, METRICS.area_icon_height)
        for row, areas in enumerate(GRID):
            for column, area in enumerate(areas):
                if (entry := by_value.get(area)) is None:
                    continue
                tile = QToolButton()
                tile.setProperty("areaTile", True)
                tile.setCheckable(True)
                tile.setChecked(entry.position == current)
                tile.setIcon(mini_screen(area, icon, theme, entry.position == current))
                tile.setIconSize(icon)
                tile.setFixedSize(METRICS.area_tile_width, METRICS.area_tile_height)
                tile.setToolTip(entry.label)
                tile.setAccessibleName(entry.label)
                tile.clicked.connect(lambda _=False, position=entry.position: self._choose(position))
                tile.installEventFilter(self)
                self._names[tile] = entry.label
                group.addButton(tile)
                cells.addWidget(tile, row, column)

        self.name = QLabel(current_label)
        self.name.setProperty("muted", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*(METRICS.space(1) + METRICS.space(1) // 2,) * 4)
        layout.setSpacing(METRICS.space(1))
        layout.addLayout(cells)
        layout.addWidget(self.name)
        self._current_label = current_label
        for entry in entries:
            if isinstance(entry.value, ScreenArea):
                continue
            other = QPushButton(entry.label)
            other.setProperty("areaOther", True)
            other.setCheckable(True)
            other.setChecked(entry.position == current)
            other.setToolTip(entry.tooltip)
            other.clicked.connect(lambda _=False, position=entry.position: self._choose(position))
            layout.addWidget(other)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paints the background and border of the stylesheet, which a translucent window does not paint itself."""
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)
        painter.end()

    def tiles(self) -> list[QToolButton]:
        return self.findChildren(QToolButton)

    def show_under(self, anchor: QWidget) -> None:
        """Shows the grid under a widget, aligned on its left, or above it when there is no room below."""
        self.adjustSize()
        below = anchor.mapToGlobal(QPoint(0, anchor.height() + METRICS.space(1)))
        screen = anchor.screen() or QGuiApplication.primaryScreen()
        room = screen.availableGeometry()
        if below.y() + self.height() > room.bottom():
            below = anchor.mapToGlobal(QPoint(0, -self.height() - METRICS.space(1)))
        x = min(max(below.x(), room.left()), room.right() - self.width())
        self.move(x, max(below.y(), room.top()))
        self.show()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched in self._names:
            if event.type() == QEvent.Type.Enter:
                self.name.setText(self._names[watched])
            elif event.type() == QEvent.Type.Leave:
                self.name.setText(self._current_label)
        return super().eventFilter(watched, event)

    def _choose(self, position: int) -> None:
        self.chosen.emit(position)
        self.close()
