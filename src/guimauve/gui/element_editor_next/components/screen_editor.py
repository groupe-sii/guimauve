"""Editor of the screens where the element is searched: one screen, all of them, or an ordered list."""

from functools import partial
from typing import Any

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag, QDragEnterEvent, QDropEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMenu, QToolButton, QWidget

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.components.buttons import IconButton
from guimauve.gui.element_editor_next.components.editors import SEPARATOR, ComboEditor, Option
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

_MULTIPLE = object()
"""Option that starts a list of screens."""

_MIME = "application/x-guimauve-screen-pill"
_NOT_CONNECTED = "This screen is not connected to this machine"


def screen_label(number: int, screens: tuple[Screen, ...]) -> str:
    """Number, role and size of a screen, e.g. "1 · Primary · 1920 × 1080"."""
    if not screens:
        return f"Screen {number}"
    if number >= len(screens):
        return f"{number} · Not connected"
    screen = screens[number]
    primary = " · Primary" if number == 1 else ""
    return f"{number}{primary} · {screen.width} × {screen.height}"


class ScreenEditor(ComboEditor):
    """All screens, one screen of the driver, or several screens in order, shown as pills under the list.

    A screen missing from the machine keeps its entry: the validation reports it as a warning.
    """

    _screens: tuple[Screen, ...] = ()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._pills = ScreenPills(theme)
        self._pills.changed.connect(self.edited)
        self.add_below(self._pills)
        self._pills.hide()

    def set_screens(self, screens: list[Screen]) -> None:
        """Screens of the driver, as Driver.screens(): 0 bounds all of them, then 1 to n."""
        if tuple(screens) != self._screens:
            self._screens = tuple(screens)
            self.refresh()
            self._show_pills()

    def set_value(self, value: Any, own: bool, inherited: Any) -> None:
        super().set_value(value, own, inherited)
        self._show_pills()

    def options(self, value: Any) -> list[Option | object]:
        screens = [Option(n, screen_label(n, self._screens)) for n in range(1, len(self._screens))]
        if isinstance(value, int) and value > 0 and value >= len(self._screens):
            tooltip = _NOT_CONNECTED if self._screens else ""
            screens.append(Option(value, screen_label(value, self._screens), tooltip))

        options: list[Option | object] = [Option(0, "All screens")]
        if screens:
            options += [SEPARATOR, *screens]
        multiple = Option(value, "Multiple screens") if isinstance(value, list) else Option(_MULTIPLE, "Multiple…")
        return [*options, SEPARATOR, multiple]

    def chosen(self, value: Any) -> Any:
        """Multiple… starts a list with the current screen, or with the primary one after All screens."""
        if value is not _MULTIPLE:
            return value
        return [self._value] if isinstance(self._value, int) and self._value > 0 else [1]

    def _show_pills(self) -> None:
        if isinstance(self._value, list):
            self._pills.set_screens(self._value, self._screens)
        self._pills.setVisible(isinstance(self._value, list))


class ScreenPills(QWidget):
    """Ordered screens as pills: + adds one, the cross removes one, drag and drop or Alt+Left/Right moves one.

    The last pill cannot be removed, since a list of screens is never empty.
    """

    changed = Signal(object)
    """The user changed the list, which is given."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self._numbers: list[int] = []
        self._screens: tuple[Screen, ...] = ()
        self._pills: list[_Pill] = []
        self._focus: int | None = None
        self.setAcceptDrops(True)

        self._add = IconButton(Icon.PLUS, theme, "Add a screen")
        self._add.setProperty("noIndicator", True)
        self._add.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._add.setMenu(QMenu(self._add))

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(METRICS.space(1))
        self._layout.addWidget(self._add)
        self._layout.addStretch()

    def set_screens(self, numbers: list[int], screens: tuple[Screen, ...]) -> None:
        """Shows the list, emitting nothing; the pill moved by the keyboard keeps the focus."""
        self._numbers, self._screens = list(numbers), screens
        for pill in self._pills:
            pill.hide()
            pill.deleteLater()
        self._pills = [_Pill(index, number, screens, self._theme, self) for index, number in enumerate(numbers)]
        for index, pill in enumerate(self._pills):
            pill.set_removable(len(numbers) > 1)
            self._layout.insertWidget(index, pill)
            pill.show()  # at once, for the focus below
        self._fill_menu()
        if self._focus is not None and self._focus < len(self._pills):
            self._pills[self._focus].setFocus()
        self._focus = None

    def add_screen(self, number: int) -> None:
        self.changed.emit([*self._numbers, number])

    def remove_screen(self, index: int) -> None:
        if len(self._numbers) > 1:
            self.changed.emit(self._numbers[:index] + self._numbers[index + 1 :])

    def move_screen(self, index: int, to: int) -> None:
        """Moves the screen at index to the position to, in the list without it."""
        to = max(0, min(to, len(self._numbers) - 1))
        if to != index:
            numbers = self._numbers.copy()
            numbers.insert(to, numbers.pop(index))
            self.changed.emit(numbers)

    def step(self, index: int, step: int) -> None:
        """Moves a screen by one place from the keyboard; its pill keeps the focus once the list is shown again."""
        to = max(0, min(index + step, len(self._numbers) - 1))
        if to != index:
            self._focus = to
            self.move_screen(index, to)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        index = int(event.mimeData().data(_MIME).data())
        x = event.position().x()
        others = [pill for pill in self._pills if pill.index != index]
        self.move_screen(index, sum(1 for pill in others if pill.geometry().center().x() < x))
        event.acceptProposedAction()

    def _fill_menu(self) -> None:
        menu = self._add.menu()
        menu.clear()
        for number in range(1, len(self._screens)):
            if number not in self._numbers:
                menu.addAction(screen_label(number, self._screens), partial(self.add_screen, number))
        self._add.setVisible(not menu.isEmpty())


class _Pill(QFrame):
    """One screen of the list: its number, the size in the tooltip, and a cross."""

    def __init__(self, index: int, number: int, screens: tuple[Screen, ...], theme: ThemeManager, owner: ScreenPills):
        super().__init__(owner)
        self.index, self._owner = index, owner
        self._pressed: QPoint | None = None
        self.setProperty("screenPill", True)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setFixedHeight(METRICS.control_height)
        self.setToolTip(_NOT_CONNECTED if screens and number >= len(screens) else screen_label(number, screens))

        self._remove = IconButton(Icon.X, theme, "Remove this screen")
        self._remove.setFixedSize(METRICS.icon + METRICS.space(1), METRICS.icon + METRICS.space(1))
        self._remove.clicked.connect(lambda: owner.remove_screen(index))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(2), 0, METRICS.space(1), 0)
        layout.setSpacing(METRICS.space(1))
        layout.addWidget(QLabel(str(number)))
        layout.addWidget(self._remove)

    def set_removable(self, removable: bool) -> None:
        self._remove.setVisible(removable)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        steps = {Qt.Key.Key_Left: -1, Qt.Key.Key_Right: 1}
        if event.modifiers() == Qt.KeyboardModifier.AltModifier and event.key() in steps:
            self._owner.step(self.index, steps[Qt.Key(event.key())])
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pressed is None:
            return
        if (event.position().toPoint() - self._pressed).manhattanLength() < QApplication.startDragDistance():
            return
        self._pressed = None
        data = QMimeData()
        data.setData(_MIME, str(self.index).encode())
        drag = QDrag(self)
        drag.setMimeData(data)
        drag.setPixmap(self.grab())
        drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._pressed = None
        super().mouseReleaseEvent(event)
