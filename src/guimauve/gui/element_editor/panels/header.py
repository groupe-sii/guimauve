"""Header of the window: the element, its issues, undo / redo, the theme, and how to leave the editor."""

from PySide6.QtCore import QSettings, QSize, Signal
from PySide6.QtGui import QActionGroup, QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

from guimauve.gui.element_editor.components import (
    Badge,
    Button,
    CenteredLabel,
    Count,
    CountBadge,
    IconButton,
    SegmentedControl,
    Variant,
    add_choice,
    add_title,
    styled_menu,
    text_icon_button,
    with_shortcut,
)
from guimauve.gui.element_editor.contract import ResumeMode
from guimauve.gui.element_editor.panels.wording import plural
from guimauve.gui.element_editor.schema import SECTIONS
from guimauve.gui.element_editor.state import Mode, Severity, Source, Store
from guimauve.gui.element_editor.system import Platform, current_platform
from guimauve.gui.element_editor.theme import METRICS, Icon, ThemeChoice, ThemeManager

SAVE = QKeySequence.StandardKey.Save
UNDO = QKeySequence.StandardKey.Undo
REDO = QKeySequence.StandardKey.Redo
TEST = "F5"
BACK_TO_EDIT = "Shift+F5"
"""F5 runs the test again while testing, as debuggers do; Shift+F5 stops, as they do."""
"""Shortcuts shown by the header and bound by the window; a key sequence is only built once the app runs."""

RESUME_LABELS = {
    ResumeMode.NOW: "Now",
    ResumeMode.AFTER_3_S: "After 3 s",
    ResumeMode.AFTER_5_S: "After 5 s",
    ResumeMode.AFTER_10_S: "After 10 s",
    ResumeMode.PAUSED: "Stay paused, until you resume",
}
RESUME_SHORT = {
    ResumeMode.NOW: "Now",
    ResumeMode.AFTER_3_S: "3 s",
    ResumeMode.AFTER_5_S: "5 s",
    ResumeMode.AFTER_10_S: "10 s",
    ResumeMode.PAUSED: "Paused",
}
RESUME_ICONS = {
    ResumeMode.NOW: Icon.PLAY,
    ResumeMode.AFTER_3_S: Icon.TIMER,
    ResumeMode.AFTER_5_S: Icon.TIMER,
    ResumeMode.AFTER_10_S: Icon.TIMER,
    ResumeMode.PAUSED: Icon.PAUSE,
}
THEME_ICONS = {ThemeChoice.SYSTEM: Icon.MONITOR, ThemeChoice.LIGHT: Icon.SUN, ThemeChoice.DARK: Icon.MOON}
_RESUME_KEY = "editor/resume"
TEST_LABEL = "Test"
EDIT_LABEL = "Back to edit"
DESCRIPTORS = [field for section in SECTIONS for field in section.fields]


class Header(QFrame):
    """Top of the window.

    On the left the name, with badges that sum up the element as the section headers do; on the right undo / redo,
    the theme, Test, and how to leave, apart from each other by thin lines. Editing is the default; Test enters
    the Test mode of the whole editor, and while testing its place holds Back to edit, tinted with the accent.
    Opened during a run, the editor offers Skip and Save and resume, with the resume mode in a menu, remembered and
    used by Skip too; from the CLI, Cancel and Save. The shortcuts are bound by the window.

    :param settings: Where the resume mode is remembered.
    :param from_run: Opened during a run, as Context.from_run.
    """

    save_requested = Signal()
    skip_requested = Signal()

    def __init__(
        self, store: Store, theme: ThemeManager, settings: QSettings, from_run: bool, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setProperty("header", True)
        self._store, self._theme, self._settings = store, theme, settings
        self._resume = self._read_resume()

        caption = CenteredLabel("Element")
        caption.setProperty("muted", True)
        self._name = CenteredLabel()
        self._name.setProperty("elementName", True)

        self._own = Badge()
        self._own.setToolTip("Values set on the element")
        self._code = CountBadge(Count.CODE, theme)
        self._code.setToolTip("Values set in the code for this call")
        self._errors = CountBadge(Count.ERROR, theme)
        self._warnings = CountBadge(Count.WARNING, theme)

        self._undo = IconButton(Icon.UNDO, theme, "Undo", QKeySequence(UNDO))
        self._undo.clicked.connect(store.undo)
        self._redo = IconButton(Icon.REDO, theme, "Redo", QKeySequence(REDO))
        self._redo.clicked.connect(store.redo)
        self._test = text_icon_button(TEST_LABEL, Icon.PLAY, theme)
        self._test.setToolTip(with_shortcut("Test the element", QKeySequence(TEST)))
        self._test.clicked.connect(lambda: store.set_mode(Mode.TEST))
        self._edit = text_icon_button(EDIT_LABEL, Icon.X, theme)  # the place of Test while testing, tinted
        self._edit.setProperty("tinted", True)
        self._edit.setToolTip(with_shortcut("Back to editing the element", QKeySequence(BACK_TO_EDIT)))
        self._edit.clicked.connect(lambda: store.set_mode(Mode.EDIT))
        self._theme_button = self._theme_selector()
        self._paint_theme_icons()

        self._skip = Button("Skip" if from_run else "Cancel")
        self._skip.setToolTip("Close without saving")
        self._skip.clicked.connect(self.skip_requested)
        self._save = Button("Save and resume" if from_run else "Save", Variant.PRIMARY)
        self._save.clicked.connect(self.save_requested)
        self._resume_button: Button | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(4), METRICS.space(3), METRICS.space(4), METRICS.space(3))
        layout.setSpacing(METRICS.space(2))
        left, left_layout = _group([caption, self._name, self._own, self._code, self._errors, self._warnings])
        left_layout.addStretch()
        save = QHBoxLayout()
        save.setSpacing(1)  # the line between the two parts of the split button
        save.addWidget(self._save)
        if from_run:
            self._save.setProperty("split", "main")
            self._resume_button = self._resume_selector()
            save.addWidget(self._resume_button)
        right, right_layout = _group(
            [self._undo, self._redo, _divider(), self._theme_button, _divider(), self._test, self._edit, self._skip]
        )
        right_layout.addLayout(save)
        layout.addWidget(left, 1)
        layout.addWidget(right)

        store.document_changed.connect(self.refresh)
        store.mode_changed.connect(self.refresh)
        self.refresh()

    @property
    def resume_mode(self) -> ResumeMode:
        """How the run resumes after Save or Skip; Now from the CLI."""
        return self._resume if self._resume_button is not None else ResumeMode.NOW

    def refresh(self) -> None:
        store = self._store
        self._name.setText(store.document.element.name)
        self._show_counts()

        testing = store.mode is Mode.TEST
        self._test.setVisible(not testing)
        self._edit.setVisible(testing)
        self._undo.setEnabled(store.can_undo)
        self._undo.setToolTip(with_shortcut(_labelled("Undo", store.undo_label), QKeySequence(UNDO)))
        self._redo.setEnabled(store.can_redo)
        self._redo.setToolTip(with_shortcut(_labelled("Redo", store.redo_label), QKeySequence(REDO)))

        errors = sum(issue.severity is Severity.ERROR for issue in store.issues)
        self._save.setEnabled(store.can_save)
        self._save.setToolTip(
            with_shortcut("Save", QKeySequence(SAVE)) if store.can_save else f"Fix {plural(errors, 'issue')} to save"
        )

    # Counts

    def _show_counts(self) -> None:
        """Sums up the badges of the sections: values set, code values that apply, errors and warnings."""
        store = self._store
        own = code = 0
        for descriptor in DESCRIPTORS:
            resolutions = [store.resolve(key) for key in descriptor.keys]
            own += any(Source.ELEMENT in resolution.layers for resolution in resolutions)
            code += any(resolution.source is Source.CODE for resolution in resolutions)
        self._own.setText(str(own))
        self._own.setVisible(own > 0)
        self._code.set_count(code)
        self._errors.set_count(sum(issue.severity is Severity.ERROR for issue in store.issues))
        self._warnings.set_count(sum(issue.severity is Severity.WARNING for issue in store.issues))

    # Theme

    def _theme_selector(self) -> SegmentedControl:
        control = SegmentedControl([(choice, "") for choice in ThemeChoice])
        control.setToolTip("Theme")
        for choice in ThemeChoice:
            segment = control.segment(choice)
            segment.setToolTip(choice.value.capitalize())
            segment.setAccessibleName(f"{choice.value.capitalize()} theme")
            segment.setIconSize(QSize(METRICS.icon, METRICS.icon))
        control.set_value(self._theme.choice)
        control.activated.connect(self._theme.set_choice)
        self._theme.changed.connect(self._paint_theme_icons)
        return control

    def _paint_theme_icons(self) -> None:
        for choice, name in THEME_ICONS.items():
            self._theme_button.segment(choice).setIcon(self._theme.icon(name))

    # Resume

    def _resume_selector(self) -> Button:
        button = Button(RESUME_SHORT[self._resume], Variant.PRIMARY)
        button.setProperty("split", "menu")
        button.setToolTip("How the run resumes; remembered, and also used by Skip")
        menu = styled_menu(button)
        add_title(menu, "Then resume the run")
        group = QActionGroup(menu)
        for mode in ResumeMode:
            if mode is ResumeMode.PAUSED and not _pause_available():
                continue
            action = add_choice(menu, RESUME_LABELS[mode], RESUME_ICONS[mode], self._theme, group, mode is self._resume)
            action.triggered.connect(lambda _=False, mode=mode: self._choose_resume(mode))
        button.setMenu(menu)
        return button

    def _choose_resume(self, mode: ResumeMode) -> None:
        self._resume = mode
        self._settings.setValue(_RESUME_KEY, mode.value)
        assert self._resume_button is not None
        self._resume_button.setText(RESUME_SHORT[mode])

    def _read_resume(self) -> ResumeMode:
        try:
            mode = ResumeMode(self._settings.value(_RESUME_KEY, ResumeMode.NOW.value))
        except ValueError:
            return ResumeMode.NOW
        return ResumeMode.NOW if mode is ResumeMode.PAUSED and not _pause_available() else mode


def _labelled(action: str, label: str | None) -> str:
    return f"{action} {label}" if label else action


def _pause_available() -> bool:
    """The pause shortcut of the PauseManager needs a global keyboard hook, which Wayland does not allow."""
    return current_platform() is not Platform.WAYLAND


def _group(widgets: list[QWidget]) -> tuple[QWidget, QHBoxLayout]:
    """Widgets side by side, spaced as in the header, and their layout."""
    group = QWidget()
    layout = QHBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(METRICS.space(2))
    for widget in widgets:
        layout.addWidget(widget)
    return group, layout


def _divider() -> QFrame:
    """Thin vertical line between two groups of controls."""
    line = QFrame()
    line.setProperty("headerDivider", True)
    line.setFixedSize(1, METRICS.icon + METRICS.space(1))
    return line
