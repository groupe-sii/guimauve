"""Controls of the Test in the bar above the canvas: the capture searched, the code overrides, the scope, Run test."""

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from guimauve.gui.element_editor_next.canvas.source_menu import fill_source_menu
from guimauve.gui.element_editor_next.components import (
    Button,
    CenteredLabel,
    SegmentedControl,
    Switch,
    Variant,
    styled_menu,
    with_shortcut,
)
from guimauve.gui.element_editor_next.state import TestScope
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeManager

RUN = "F5"
"""Shortcut of Run test, bound by the window."""
CODE = "{} Code"
CODE_TIP = "Use the values set in the code for this call"


class TestSourceButton(QToolButton):
    """Capture the Test searches, named on the button, whose menu offers the other sources."""

    __test__ = False  # not a test class for pytest

    source_chosen = Signal(object)
    """A CaptureSource; DELAYED with the delay kept, see delay_chosen for another."""
    delay_chosen = Signal(int)
    custom_delay_requested = Signal()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self._theme = theme
        self.setProperty("capture", True)
        self.setToolTip("Capture to test on")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(METRICS.icon, METRICS.icon))
        self.setFixedHeight(METRICS.control_height)
        self.setMenu(styled_menu(self))
        self._paint()
        theme.changed.connect(self._paint)

    def set_source(self, name: str, delay: int, initial_error: str | None) -> None:
        """Names the capture and rebuilds the menu, ticking the delay kept."""
        self.setText(name)
        fill_source_menu(
            self.menu(),
            self._theme,
            "Test on",
            delay,
            initial_error,
            self.source_chosen.emit,
            self.delay_chosen.emit,
            self.custom_delay_requested.emit,
        )

    def _paint(self) -> None:
        self.setIcon(self._theme.icon(Icon.MONITOR, "text_secondary"))


class TestControls(QWidget):
    """Switch of the code overrides, shown when the code sets some, Variant / Element, and Run test."""

    __test__ = False  # not a test class for pytest

    code_toggled = Signal(bool)
    scope_chosen = Signal(object)
    """The TestScope chosen."""
    run_requested = Signal()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None):
        super().__init__(parent)
        self.code = Switch(theme)
        self.code.setToolTip(CODE_TIP)
        self.code.clicked.connect(lambda: self.code_toggled.emit(self.code.isChecked()))
        self.code_label = CenteredLabel(CODE)
        self.code_label.setToolTip(CODE_TIP)
        self.scope = SegmentedControl([(TestScope.VARIANT, "Variant"), (TestScope.ELEMENT, "Element")])
        self.scope.setToolTip("Test the selected variant alone, or every variant as a run does")
        self.scope.activated.connect(self.scope_chosen)
        self.run = Button("Run test", Variant.PRIMARY)
        self.run.clicked.connect(self.run_requested)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space(1))
        layout.addWidget(self.code)
        layout.addWidget(self.code_label)
        layout.addSpacing(METRICS.space(2))
        layout.addWidget(self.scope, 0, Qt.AlignmentFlag.AlignVCenter)  # its own height, not the bar's
        layout.addSpacing(METRICS.space(1))
        layout.addWidget(self.run)

    def set_code(self, shown: bool, included: bool) -> None:
        """Shows the switch when the code sets values for this call, on when they apply."""
        self.code.setVisible(shown)
        self.code_label.setVisible(shown)
        self.code.setChecked(included)

    def set_scope(self, scope: TestScope) -> None:
        self.scope.set_value(scope)

    def set_run(self, blocked: str | None) -> None:
        """Enables Run test, or disables it with the reason in its tooltip."""
        self.run.setEnabled(blocked is None)
        self.run.setToolTip(with_shortcut("Run test", QKeySequence(RUN)) if blocked is None else blocked)
