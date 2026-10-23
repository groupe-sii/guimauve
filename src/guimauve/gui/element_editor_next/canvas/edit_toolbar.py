"""Floating bar of the editing tools, at the top left of the canvas."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QToolButton, QWidget

from guimauve.gui.element_editor_next.canvas.tools import Tool
from guimauve.gui.element_editor_next.components import with_shortcut
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

BUTTON = 32
TOOLS = (
    (Tool.SELECT, Icon.MOUSE_POINTER, "Select", "V"),
    (Tool.TARGET, Icon.LOCATE, "Target", "T"),
    (Tool.MATCH_AREA, Icon.SQUARE_DASHED, "Match area", "M"),
    (Tool.CROP, Icon.CROP, "Crop", "C"),
)
"""Tool, icon, name and key of each button; the keys are handled by the canvas while it has the focus."""
AVAILABLE = {Tool.SELECT, Tool.TARGET}
"""Tools working so far; the others are shown disabled."""


class EditToolbar(QFrame):
    """One button per tool, the active one checked; the buttons never take the focus from the canvas."""

    tool_chosen = Signal(object)
    """A Tool, chosen with its button."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("editToolbar")
        self._theme = theme
        self._buttons: dict[Tool, QToolButton] = {}
        group = QButtonGroup(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(*[METRICS.space(1)] * 4)
        layout.setSpacing(2)
        for tool, name, text, key in TOOLS:
            button = QToolButton()
            button.setObjectName(f"tool_{tool.value}")
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedSize(BUTTON, BUTTON)
            button.setIconSize(QSize(METRICS.icon, METRICS.icon))
            button.setToolTip(with_shortcut(text, key))
            button.setEnabled(tool in AVAILABLE)
            button.toggled.connect(lambda _=False, button=button, name=name: self._paint(button, name))
            button.clicked.connect(lambda _=False, tool=tool: self.tool_chosen.emit(tool))
            group.addButton(button)
            layout.addWidget(button)
            self._buttons[tool] = button
            self._paint(button, name)
        theme.changed.connect(self._repaint)
        self.adjustSize()

    def button(self, tool: Tool) -> QToolButton:
        return self._buttons[tool]

    def show_tool(self, tool: Tool) -> None:
        self._buttons[tool].setChecked(True)

    def _paint(self, button: QToolButton, name: Icon) -> None:
        button.setIcon(self._theme.icon(name, "accent" if button.isChecked() else "text_secondary"))

    def _repaint(self) -> None:
        for (_, name, _, _), button in zip(TOOLS, self._buttons.values(), strict=True):
            self._paint(button, name)
