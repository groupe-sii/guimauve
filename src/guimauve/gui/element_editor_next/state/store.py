"""Single entry point of the panels: runs commands and notifies changes."""

from enum import Enum
from itertools import count
from typing import Any

from PySide6.QtCore import QObject, Signal

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.schema import FIELDS
from guimauve.gui.element_editor_next.state.commands import (
    ELEMENT,
    Command,
    Group,
    SetTrial,
    SetValue,
    apply_trials,
    discard_trials,
)
from guimauve.gui.element_editor_next.state.document import Document
from guimauve.gui.element_editor_next.state.history import History
from guimauve.gui.element_editor_next.state.validation import Issue, can_save, validate
from guimauve.models.element import Element
from guimauve.models.parameters import DefaultProperties
from guimauve.models.variant import Variant


class Mode(Enum):
    EDIT = "edit"
    TEST = "test"


class Store(QObject):
    """State of an editing session, shared by every panel.

    Panels never talk to each other: they send commands to the store and update themselves on its signals. The
    selection, the mode and the test result go through the store but not through the history; the trials do.

    :param document: Document to edit.
    :param default: Default values, read-only.
    :param screens: Screens of the driver, to check the screen field; None or empty when unknown.
    """

    document_changed = Signal()
    """The document changed: command, undo or redo. Issues and history flags are already up to date."""

    selection_changed = Signal()
    mode_changed = Signal()
    """The mode or one of its options (include_code) changed."""

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
        self._include_code = True
        self._variant = self._variant_keys()[0] if document.variants else None
        self._target: int | None = None
        self._test_result: Any = None
        self._test_stale = False

    @property
    def screens(self) -> list[Screen]:
        """Screens of the driver, as Driver.screens(); empty when unknown, as with VNC."""
        return list(self._screens)

    # Document

    def execute(self, command: Command) -> None:
        self._change(lambda: self._history.push(command))

    def set_field(self, owner: int | None, field: str, value: Any, label: str = "", gesture: int | None = None):
        """Sets a field of the element (ELEMENT), a variant or a target, by its key.

        In Test mode, a property of the element or a variant becomes a trial instead; other fields, such as a name,
        a target or an image, are always set on the element.
        """
        if self._mode is Mode.TEST and self._is_property(owner, field):
            self.execute(SetTrial(owner, field, value, label, gesture))
        else:
            self.execute(SetValue(owner, field, value, label, gesture))

    def set_fields(self, owner: int | None, values: dict[str, Any], label: str = "") -> None:
        """Sets several fields of one owner as one undo step, e.g. the two fields of an axis of the fixed position."""
        commands: list[Command] = []
        for field, value in values.items():
            trial = self._mode is Mode.TEST and self._is_property(owner, field)
            commands.append((SetTrial if trial else SetValue)(owner, field, value, label))
        self.execute(Group(commands, label))

    @property
    def has_trials(self) -> bool:
        return not self.document.trials.is_empty

    def apply_trials(self) -> None:
        """Writes the trials into the element, as one undoable step."""
        if self.has_trials:
            self.execute(apply_trials(self.document))

    def discard_trials(self) -> None:
        """Removes every trial, as one undoable step."""
        if self.has_trials:
            self.execute(discard_trials(self.document))

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
        """Changes the mode; the trials are kept when going back to Edit."""
        if mode is not self._mode:
            self._mode = mode
            self.mode_changed.emit()

    @property
    def include_code(self) -> bool:
        """Whether the Test applies the code overrides."""
        return self._include_code

    def set_include_code(self, include: bool) -> None:
        if include != self._include_code:
            self._include_code = include
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

    def _is_property(self, owner: int | None, field: str) -> bool:
        """True for a field of the schema that the element or this variant can hold; False for a target."""
        model = self.document.element if owner is ELEMENT else self.document.get(owner)
        if not isinstance(model, (Element, Variant)):  # a target has x and y too, never tried
            return False
        return field in FIELDS and field in type(model).model_fields

    def _variant_keys(self) -> list[int]:
        return [self.document.key(variant) for variant in self.document.variants]

    def _target_keys(self, variant: int | None) -> list[int]:
        if variant is None:
            return []
        return [self.document.key(target) for target in getattr(self.document.get(variant), "targets", None) or []]
