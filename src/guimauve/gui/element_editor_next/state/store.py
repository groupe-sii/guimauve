"""Single entry point of the panels: runs commands and notifies changes."""

from enum import Enum
from itertools import count
from typing import Any

from PySide6.QtCore import QObject, Signal

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.state.commands import ELEMENT, Command, SetValue
from guimauve.gui.element_editor_next.state.document import Document
from guimauve.gui.element_editor_next.state.history import History
from guimauve.gui.element_editor_next.state.validation import Issue, can_save, validate
from guimauve.models.element import Element
from guimauve.models.parameters import DefaultProperties


class Mode(Enum):
    EDIT = "edit"
    TEST = "test"


class Store(QObject):
    """State of an editing session, shared by every panel.

    Panels never talk to each other: they send commands to the store and update themselves on its signals. The
    selection, the mode and the test result go through the store but not through the history.

    :param document: Document to edit.
    :param default: Default values, read-only.
    :param screens: Screens of the driver, to check the screen field; None or empty when unknown.
    """

    document_changed = Signal()
    """The document changed: command, undo or redo. Issues and history flags are already up to date."""

    selection_changed = Signal()
    mode_changed = Signal()
    test_changed = Signal()
    """A test result was set, or the current one became stale."""

    def __init__(
        self,
        document: Document,
        default: DefaultProperties,
        screens: list[Screen] | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.document = document
        self.default = default
        self._screens = list(screens or [])
        self._history = History(document)
        self._issues = validate(document, self._screens)
        self._gestures = count(1)

        self._mode = Mode.EDIT
        self._variant = self._variant_keys()[0] if document.variants else None
        self._target: int | None = None
        self._test_result: Any = None
        self._test_stale = False

    # Document

    def execute(self, command: Command) -> None:
        self._change(lambda: self._history.push(command))

    def set_field(self, owner: int | None, field: str, value: Any, label: str = "", gesture: int | None = None):
        """Sets a field of the element (ELEMENT), a variant or a target, by its key."""
        self.execute(SetValue(owner, field, value, label, gesture))

    def undo(self) -> None:
        if self._history.can_undo:
            self._change(self._history.undo)

    def redo(self) -> None:
        if self._history.can_redo:
            self._change(self._history.redo)

    def new_gesture(self) -> int:
        """Returns a new identifier for a continuous edit, such as dragging a target or a slider."""
        return next(self._gestures)

    @property
    def can_undo(self) -> bool:
        return self._history.can_undo

    @property
    def can_redo(self) -> bool:
        return self._history.can_redo

    @property
    def undo_label(self) -> str | None:
        return self._history.undo_label

    @property
    def redo_label(self) -> str | None:
        return self._history.redo_label

    @property
    def is_modified(self) -> bool:
        return self.document.is_modified()

    @property
    def issues(self) -> list[Issue]:
        return list(self._issues)

    @property
    def can_save(self) -> bool:
        return can_save(self._issues)

    def issues_of(self, owner: int | None = ELEMENT, field: str | None = None) -> list[Issue]:
        """Issues of one owner; of one of its fields when field is given."""
        return [i for i in self._issues if i.owner == owner and (field is None or i.field == field)]

    def result(self) -> Element:
        """Copy of the edited element to save, without the code overrides, images still in memory."""
        return self.document.element.model_copy(deep=True)

    # Selection

    @property
    def selected_variant(self) -> int | None:
        return self._variant

    @property
    def selected_target(self) -> int | None:
        return self._target

    def select(self, variant: int | None, target: int | None = None) -> None:
        """Selects a variant, and optionally one of its targets, by their keys."""
        if (variant, target) != (self._variant, self._target):
            self._variant, self._target = variant, target
            self.selection_changed.emit()

    # Mode

    @property
    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode) -> None:
        if mode is not self._mode:
            self._mode = mode
            self.mode_changed.emit()

    # Test

    @property
    def test_result(self) -> Any:
        return self._test_result

    @property
    def test_stale(self) -> bool:
        """True once the document changed after the test result was set."""
        return self._test_stale

    def set_test_result(self, result: Any) -> None:
        self._test_result = result
        self._test_stale = False
        self.test_changed.emit()

    # Internals

    def _change(self, run) -> None:
        keys = self._variant_keys()
        index = keys.index(self._variant) if self._variant in keys else 0

        run()
        self._issues = validate(self.document, self._screens)
        self.document_changed.emit()

        self._repair_selection(index)
        if self._test_result is not None and not self._test_stale:
            self._test_stale = True
            self.test_changed.emit()

    def _repair_selection(self, index: int) -> None:
        """Moves the selection to the nearest variant when the selected variant or target is gone."""
        keys = self._variant_keys()
        variant = self._variant if self._variant in keys else (keys[min(index, len(keys) - 1)] if keys else None)
        target = self._target if variant == self._variant and self._target in self._target_keys(variant) else None
        self.select(variant, target)

    def _variant_keys(self) -> list[int]:
        return [self.document.key(variant) for variant in self.document.variants]

    def _target_keys(self, variant: int | None) -> list[int]:
        if variant is None:
            return []
        return [self.document.key(target) for target in getattr(self.document.get(variant), "targets", None) or []]
