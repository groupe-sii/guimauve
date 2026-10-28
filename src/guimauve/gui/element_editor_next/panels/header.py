"""Header of the window: the element, its issues, undo / redo, the theme, and how to leave the editor."""

from PySide6.QtCore import QSettings, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QToolButton, QWidget

from guimauve.gui.element_editor_next.components import (
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
    with_shortcut,
)
from guimauve.gui.element_editor_next.contract import ResumeMode
from guimauve.gui.element_editor_next.panels.wording import plural
from guimauve.gui.element_editor_next.schema import SECTIONS
from guimauve.gui.element_editor_next.state import Mode, Severity, Source, Store
from guimauve.gui.element_editor_next.system import Platform, current_platform
from guimauve.gui.element_editor_next.theme import METRICS, Icon, ThemeChoice, ThemeManager

SAVE = QKeySequence.StandardKey.Save
UNDO = QKeySequence.StandardKey.Undo
REDO = QKeySequence.StandardKey.Redo
TEST = "F5"
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
DESCRIPTORS = [field for section in SECTIONS for field in section.fields]


class Header(QFrame):
    """Top of the window.

    Next to the name, badges sum up the element as the section headers do. After undo / redo, Edit / Test switches
    the mode of the whole editor. Opened during a run, the editor
    offers Skip and Save and resume, with the resume mode in a menu, remembered and used by Skip too; from the
    CLI, Cancel and Save. The shortcuts are bound by the window.

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
        self._errors.setToolTip("Errors")
        self._warnings = CountBadge(Count.WARNING, theme)
        self._warnings.setToolTip("Warnings")

        self._undo = IconButton(Icon.UNDO, theme, "Undo", QKeySequence(UNDO))
        self._undo.clicked.connect(store.undo)
        self._redo = IconButton(Icon.REDO, theme, "Redo", QKeySequence(REDO))
        self._redo.clicked.connect(store.redo)
        self._mode = SegmentedControl([(Mode.EDIT, "Edit"), (Mode.TEST, "Test")])
        self._mode.setToolTip(with_shortcut("Test the element", QKeySequence(TEST)))
        self._mode.activated.connect(store.set_mode)
        self._theme_button = self._theme_selector()

        self._skip = Button("Skip" if from_run else "Cancel")
        self._skip.setToolTip("Close without saving")
        self._skip.clicked.connect(self.skip_requested)
        self._save = Button("Save and resume" if from_run else "Save", Variant.PRIMARY)
        self._save.clicked.connect(self.save_requested)
        self._resume_button: Button | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(METRICS.space(3), METRICS.space(2), METRICS.space(3), METRICS.space(2))
        layout.setSpacing(METRICS.space(2))
        summary: list[QWidget] = [caption, self._name, self._own, self._code, self._errors, self._warnings]
        for widget in summary:
            layout.addWidget(widget)
        layout.addStretch()
        for button in (self._undo, self._redo, self._mode, self._theme_button):
            layout.addWidget(button)
        layout.addSpacing(METRICS.space(2))
        layout.addWidget(self._skip)
        save = QHBoxLayout()
        save.setSpacing(1)  # the line between the two parts of the split button
        save.addWidget(self._save)
        if from_run:
            self._save.setProperty("split", "main")
            self._resume_button = self._resume_selector()
            save.addWidget(self._resume_button)
        layout.addLayout(save)

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

        self._mode.set_value(store.mode)
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

    def _theme_selector(self) -> IconButton:
        button = IconButton(THEME_ICONS[self._theme.choice], self._theme, "Theme")
        button.setProperty("noIndicator", True)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        group = QActionGroup(menu)
        for choice in ThemeChoice:
            action = QAction(choice.value.capitalize(), menu, checkable=True, checked=choice is self._theme.choice)
            action.triggered.connect(lambda _=False, choice=choice: self._choose_theme(choice))
            group.addAction(action)
            menu.addAction(action)
        button.setMenu(menu)
        return button

    def _choose_theme(self, choice: ThemeChoice) -> None:
        self._theme.set_choice(choice)
        self._theme_button.set_icon(THEME_ICONS[choice])

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
