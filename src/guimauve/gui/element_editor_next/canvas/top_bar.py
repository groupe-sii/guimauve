"""Bar above the canvas; for now, the zoom."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QToolButton, QWidget

from guimauve.gui.element_editor_next.canvas import zoom as zooms
from guimauve.gui.element_editor_next.canvas.status_bar import tabular
from guimauve.gui.element_editor_next.components import IconButton, add_item, add_title, styled_menu
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

FIT = "Ctrl+0"
ACTUAL_SIZE = "Ctrl+1"
ZOOM_IN = QKeySequence.StandardKey.ZoomIn
ZOOM_OUT = QKeySequence.StandardKey.ZoomOut
ZOOM_IN_EXTRA = "Ctrl+="
"""Zoom in without Shift on keyboards where + is above =; bound by the canvas panel with the others."""


def preset_text(zoom: float) -> str:
    return "Actual size (100 %)" if zoom == 1.0 else zooms.label(zoom)


class CanvasTopBar(QFrame):
    """Zoom out, the zoom level opening a menu of levels, zoom in; the shortcuts are bound by the canvas panel."""

    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    fit_requested = Signal()
    zoom_requested = Signal(float)

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("canvasBar")
        self.setFixedHeight(METRICS.canvas_bar_height)

        self.zoom_out = IconButton(Icon.MINUS, theme, "Zoom out", QKeySequence(ZOOM_OUT))
        self.zoom_out.clicked.connect(self.zoom_out_requested)
        self.zoom_in = IconButton(Icon.PLUS, theme, "Zoom in", QKeySequence(ZOOM_IN))
        self.zoom_in.clicked.connect(self.zoom_in_requested)

        self.zoom_menu = styled_menu(self)
        add_title(self.zoom_menu, "Zoom")
        fit = add_item(self.zoom_menu, _with_keys("Fit to window", FIT), Icon.SCAN, theme)
        fit.triggered.connect(self.fit_requested)
        self.zoom_menu.addSeparator()
        for level in zooms.PRESETS:
            action = QAction(_with_keys(preset_text(level), ACTUAL_SIZE if level == 1.0 else None), self.zoom_menu)
            action.triggered.connect(lambda _=False, level=level: self.zoom_requested.emit(level))
            self.zoom_menu.addAction(action)

        self.zoom_button = QToolButton()
        self.zoom_button.setProperty("zoom", True)
        self.zoom_button.setToolTip("Zoom level")
        self.zoom_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.zoom_button.setMenu(self.zoom_menu)
        self.zoom_button.setFixedHeight(METRICS.control_height)
        tabular(self.zoom_button)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(2), 0, METRICS.space(2), 0)
        layout.setSpacing(METRICS.space(1))
        layout.addStretch()
        layout.addWidget(self.zoom_out)
        layout.addWidget(self.zoom_button)
        layout.addWidget(self.zoom_in)
        self.show_zoom(1.0)

    def show_zoom(self, zoom: float | None) -> None:
        """Shows the zoom level, or hides the zoom controls when there is no image."""
        self.zoom_button.setText("" if zoom is None else zooms.label(zoom))
        for widget in (self.zoom_out, self.zoom_button, self.zoom_in):
            widget.setVisible(zoom is not None)


def _with_keys(text: str, keys: str | None) -> str:
    """Menu text with its shortcut in the shortcut column, written as the system does."""
    if keys is None:
        return text
    return f"{text}\t{QKeySequence(keys).toString(QKeySequence.SequenceFormat.NativeText)}"
