"""Bar above the canvas: the capture menu, a countdown, an error or help on the active tool, then the zoom."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QToolButton, QWidget

from guimauve.gui.element_editor_next.canvas import zoom as zooms
from guimauve.gui.element_editor_next.canvas.status_bar import tabular
from guimauve.gui.element_editor_next.components import (
    CHECK,
    Button,
    CenteredLabel,
    IconButton,
    IconLabel,
    Variant,
    add_item,
    add_title,
    styled_menu,
)
from guimauve.gui.element_editor_next.services import CaptureSource
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

FIT = "Ctrl+0"
ACTUAL_SIZE = "Ctrl+1"
ZOOM_IN = QKeySequence.StandardKey.ZoomIn
ZOOM_OUT = QKeySequence.StandardKey.ZoomOut
HELP_ICON = 14
ZOOM_IN_EXTRA = "Ctrl+="
"""Zoom in without Shift on keyboards where + is above =; bound by the canvas panel with the others."""


CAPTURE_DELAYS = (1, 3, 5, 10)
COUNTDOWN = "Capturing in {seconds} s"


def preset_text(zoom: float) -> str:
    return "Actual size (100 %)" if zoom == 1.0 else zooms.label(zoom)


class CanvasTopBar(QFrame):
    """Capture or Recapture with its menu, a message, then zoom out, the zoom level opening a menu of levels, zoom in.

    The message is the countdown of a delayed capture with Cancel, else the last capture error with a close button,
    else the help on the active tool. The shortcuts are bound by the canvas panel.
    """

    capture_requested = Signal(object)
    """A CaptureSource chosen in the menu; DELAYED with the delay kept, see delay_chosen for another."""
    delay_chosen = Signal(int)
    """A delay chosen in the submenu, in seconds, to capture after."""
    custom_delay_requested = Signal()
    countdown_cancelled = Signal()
    error_closed = Signal()
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

        self._theme = theme
        self.capture_menu = styled_menu(self)
        self.capture_button = QToolButton()
        self.capture_button.setProperty("capture", True)
        self.capture_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.capture_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.capture_button.setIconSize(QSize(METRICS.icon, METRICS.icon))
        self.capture_button.setFixedHeight(METRICS.control_height)
        self.capture_button.setMenu(self.capture_menu)
        self._paint_capture()
        theme.changed.connect(self._paint_capture)

        self.help_icon = IconLabel(Icon.INFO, theme, "text_muted", HELP_ICON)
        self.help = CenteredLabel()
        self.help.setProperty("muted", True)
        self._help: str | None = None
        self.countdown = CenteredLabel()
        self.countdown.setProperty("fieldLabel", True)
        tabular(self.countdown)
        self.cancel_countdown = Button("Cancel", Variant.GHOST)
        self.cancel_countdown.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_countdown.clicked.connect(self.countdown_cancelled)
        self.error_icon = IconLabel(Icon.CIRCLE_ALERT, theme, "error", HELP_ICON)
        self.error = CenteredLabel()
        self.error.setProperty("message", "error")
        self.close_error = IconButton(Icon.X, theme, "Dismiss")
        self.close_error.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_error.clicked.connect(self.error_closed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(2), 0, METRICS.space(2), 0)
        layout.setSpacing(METRICS.space(1))
        help_row = QHBoxLayout()
        help_row.setContentsMargins(METRICS.space(1), 0, 0, 0)
        help_row.setSpacing(METRICS.space(1) + 2)
        for widget in (
            self.help_icon,
            self.help,
            self.countdown,
            self.cancel_countdown,
            self.error_icon,
            self.error,
            self.close_error,
        ):
            help_row.addWidget(widget)
        layout.addWidget(self.capture_button)
        layout.addLayout(help_row)
        layout.addStretch()
        layout.addWidget(self.zoom_out)
        layout.addWidget(self.zoom_button)
        layout.addWidget(self.zoom_in)
        self.show_zoom(1.0)
        self.set_capture(False)
        self._countdown: int | None = None
        self._error: str | None = None
        self._show_message()

    def set_capture(
        self, shown: bool, recapture: bool = False, delay: int = 3, initial_error: str | None = None
    ) -> None:
        """Shows Capture, or Recapture for a variant with an image, or nothing; its menu ticks the delay kept.

        :param initial_error: Why Initial screen is disabled, the screens not captured at opening.
        """
        self.capture_button.setVisible(shown)
        self.capture_button.setText("Recapture" if recapture else "Capture")
        self._build_capture_menu(delay, initial_error)

    def show_help(self, text: str | None) -> None:
        """Shows how to use the active tool, or nothing, once no countdown nor error is shown."""
        self._help = text
        self._show_message()

    def show_countdown(self, seconds: int | None) -> None:
        self._countdown = seconds
        self._show_message()

    def show_error(self, text: str | None) -> None:
        self._error = text
        self._show_message()

    def _show_message(self) -> None:
        countdown, error = self._countdown, self._error
        self.countdown.setText("" if countdown is None else COUNTDOWN.format(seconds=countdown))
        self.error.setText(error or "")
        self.help.setText(self._help or "")
        shown = "countdown" if countdown is not None else "error" if error is not None else "help"
        groups: tuple[tuple[tuple[QWidget, ...], bool], ...] = (
            ((self.countdown, self.cancel_countdown), shown == "countdown"),
            ((self.error_icon, self.error, self.close_error), shown == "error"),
            ((self.help_icon, self.help), shown == "help" and self._help is not None),
        )
        for widgets, visible in groups:
            for widget in widgets:
                widget.setVisible(visible)

    def _build_capture_menu(self, delay: int, initial_error: str | None) -> None:
        menu, theme = self.capture_menu, self._theme
        menu.clear()
        add_title(menu, "Capture")
        initial = add_item(menu, "Initial screen\tat opening", Icon.MONITOR, theme, enabled=initial_error is None)
        initial.setToolTip(initial_error or "")
        initial.triggered.connect(lambda: self.capture_requested.emit(CaptureSource.INITIAL))
        instant = add_item(menu, "Instant\tnow", Icon.CAMERA, theme)
        instant.triggered.connect(lambda: self.capture_requested.emit(CaptureSource.INSTANT))
        delays = styled_menu(menu)
        for seconds in CAPTURE_DELAYS:
            action = QAction(f"{seconds} s" + (CHECK if seconds == delay else ""), delays)
            action.triggered.connect(lambda _=False, seconds=seconds: self.delay_chosen.emit(seconds))
            delays.addAction(action)
        custom = QAction("Custom…" + (CHECK if delay not in CAPTURE_DELAYS else ""), delays)
        custom.triggered.connect(self.custom_delay_requested)
        delays.addAction(custom)
        later = _add_submenu(menu, delays, f"After a delay\t{delay} s", Icon.TIMER, theme)
        later.setObjectName("captureLater")
        menu.addSeparator()
        file = add_item(menu, "Import a file…", Icon.IMAGE_UP, theme)
        file.triggered.connect(lambda: self.capture_requested.emit(CaptureSource.FILE))

    def _paint_capture(self) -> None:
        self.capture_button.setIcon(self._theme.icon(Icon.CAMERA, "text_secondary"))

    def show_zoom(self, zoom: float | None) -> None:
        """Shows the zoom level, or hides the zoom controls when there is no image."""
        self.zoom_button.setText("" if zoom is None else zooms.label(zoom))
        for widget in (self.zoom_out, self.zoom_button, self.zoom_in):
            widget.setVisible(zoom is not None)


def _add_submenu(menu: QMenu, submenu: QMenu, text: str, name: Icon, theme: ThemeManager) -> QAction:
    action = menu.addMenu(submenu)
    action.setText(text)
    action.setIcon(theme.icon(name))
    return action


def _with_keys(text: str, keys: str | None) -> str:
    """Menu text with its shortcut in the shortcut column, written as the system does."""
    if keys is None:
        return text
    return f"{text}\t{QKeySequence(keys).toString(QKeySequence.SequenceFormat.NativeText)}"
