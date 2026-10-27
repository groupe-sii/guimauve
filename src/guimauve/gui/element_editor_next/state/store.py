"""Single entry point of the panels: runs commands and notifies changes."""

import copy
from enum import Enum
from itertools import count
from typing import Any

import numpy as np
from PySide6.QtCore import QObject, Signal

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.schema import FIELDS
from guimauve.gui.element_editor_next.state.cascade import Resolution, resolve
from guimauve.gui.element_editor_next.state.commands import (
    ELEMENT,
    Command,
    Group,
    SetTrial,
    SetValue,
    apply_trials,
    discard_trials,
    insert,
    move,
    remove,
)
from guimauve.gui.element_editor_next.state.document import Document, Trials
from guimauve.gui.element_editor_next.state.geometry import crop_image, cropped_match_area, intersect, match_area, whole
from guimauve.gui.element_editor_next.state.history import History
from guimauve.gui.element_editor_next.state.validation import Issue, can_save, validate
from guimauve.gui.element_editor_next.state.variants import VariantSummary, duplicate, normalize_name, summarize
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.parameters import DefaultProperties
from guimauve.models.variant import ImageVariant, Target, TextVariant, Variant


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
    """The mode or one of its options (include_code) changed; the resolved values may have changed with it."""

    test_changed = Signal()
    """A test result was set, or the current one became stale."""

    match_area_edit_requested = Signal()
    """A panel asks to edit the match area of the selected variant on the image."""

    text_edit_requested = Signal()
    """A panel asks to type the text of the selected text variant."""

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
        """Copy of the edited element to save, without the code overrides, images still in memory.

        The texts of the text variants lose their leading and trailing spaces, even one saved while still typed.
        """
        element = self.document.element.model_copy(deep=True)
        for variant in element.variants or []:
            if isinstance(variant, TextVariant):
                variant.text = variant.text.strip()
        return element

    def resolve(self, field: str, variant: int | None = None) -> Resolution:
        """Resolves a field of the element, or of a variant by its key, as the mode shows it.

        Edit shows the values to save, with the code overrides and without the trials; Test applies the trials,
        and the code overrides as include_code says.
        """
        model = None if variant is None else self.document.get(variant)
        if self._mode is Mode.TEST:
            return resolve(field, self.document, self.default, model, include_code=self._include_code)
        return resolve(field, self.document, self.default, model, Trials())

    # Variants

    def add_variant(self, variant: Variant, index: int | None = None) -> int:
        """Adds a variant, at the end by default, and selects it; returns its key."""
        self.execute(insert(self.document, ELEMENT, "variants", variant, index, "Add variant"))
        key = self.document.key(variant)
        self.select(key)
        return key

    def duplicate_variant(self, key: int) -> int:
        """Adds a copy of a variant just after it, under a free name, and selects it; returns its key."""
        names = [variant.name for variant in self.document.variants]
        copy = duplicate(self.document.get(key), names)
        index = self._variant_keys().index(key) + 1
        self.execute(insert(self.document, ELEMENT, "variants", copy, index, "Duplicate variant"))
        new = self.document.key(copy)
        self.select(new)
        return new

    def remove_variant(self, key: int) -> None:
        """Removes a variant; the selection moves to the nearest one."""
        self.execute(remove(self.document, ELEMENT, "variants", key, "Delete variant"))

    def move_variant(self, key: int, index: int) -> None:
        """Moves a variant to a position of the list; does nothing out of the list or in place."""
        keys = self._variant_keys()
        if 0 <= index < len(keys) and keys.index(key) != index:
            self.execute(move(self.document, ELEMENT, "variants", key, index, "Move variant"))

    def rename_variant(self, key: int, name: str) -> bool:
        """Renames a variant, also in Test mode, with the name normalized (MY_NAME).

        :return: False when the name is refused, being empty or taken by another variant.
        """
        name = normalize_name(name)
        current = self.document.get(key).name
        if not name or any(v.name == name for v in self.document.variants if v is not self.document.get(key)):
            return False
        if name != current:
            self.execute(SetValue(key, "name", name, "Rename variant"))
        return True

    def override(self, key: int, field: str, label: str = "") -> None:
        """Sets a property on a variant to the value it inherits, so it can be changed there; a trial in Test mode."""
        value = self.resolve(field, key)
        if value.value is not None:
            self.set_field(key, field, copy.deepcopy(value.value), f"Override {label or field}")

    def rename_target(self, variant: int, target: int, name: str | None) -> None:
        """Renames a target, None to remove its name; the default target of the variant follows."""
        old = self.document.get(target).name
        if name == old:
            return
        commands: list[Command] = [SetValue(target, "name", name)]
        if old is not None and self.document.get(variant).default_target == old:
            commands.append(SetValue(variant, "default_target", name))
        self.execute(Group(commands, "Rename target"))

    def remove_target(self, variant: int, target: int) -> None:
        """Removes a target; the variant no longer uses it as its default target."""
        name = self.document.get(target).name
        commands: list[Command] = [remove(self.document, variant, "targets", target)]
        if name is not None and self.document.get(variant).default_target == name:
            commands.append(SetValue(variant, "default_target", None))
        self.execute(Group(commands, "Delete target"))

    # Image variants

    def add_target(self, variant: int, x: int, y: int) -> int:
        """Adds an unnamed target at a pixel, inside the image or not, and selects it; returns its key."""
        target = Target(x=x, y=y)
        self.execute(insert(self.document, variant, "targets", target, label="Add target"))
        key = self.document.key(target)
        self.select(variant, key)
        return key

    def move_target(self, target: int, x: int, y: int, gesture: int | None = None) -> None:
        """Moves a target to a pixel, inside the image or not; a drag passes one gesture for all its moves.

        A target outside the image is kept, as in the files of older versions, and reported by the validation.
        """
        current = self.document.get(target)
        if (x, y) != (current.x, current.y):
            values = (SetValue(target, field, value, gesture=gesture) for field, value in (("x", x), ("y", y)))
            self.execute(Group(list(values), "Move target", gesture))

    def nudge_target(self, target: int, dx: int, dy: int) -> None:
        """Moves a target by a number of pixels, e.g. with the arrow keys."""
        current = self.document.get(target)
        self.move_target(target, current.x + dx, current.y + dy)

    def set_match_area(self, variant: int, area: Area | None) -> None:
        """Sets the part of the image compared, clipped to it; the whole image, or nothing left, is stored as None."""
        area = match_area(area, *self._size(variant))
        if area != self.document.get(variant).match_area:
            self.execute(SetValue(variant, "match_area", area, "Match area"))

    def replace_image(self, variant: int, image: np.ndarray) -> None:
        """Replaces the image, e.g. by a new capture; the targets stay, the match area becomes the whole image.

        A target outside the new image is kept and reported by the validation.
        """
        commands: list[Command] = [SetValue(variant, "image", image)]
        if self.document.get(variant).match_area is not None:
            commands.append(SetValue(variant, "match_area", None))
        self.execute(Group(commands, "Replace image"))

    def crop(self, variant: int, area: Area) -> bool:
        """Crops the image; the targets move with it, those left outside are kept, the match area is clipped.

        :return: False when nothing is cropped, the area covering the whole image or lying outside it.
        """
        owner: ImageVariant = self.document.get(variant)
        width, height = self._size(variant)
        crop = intersect(area, whole(width, height))
        if crop is None or crop == whole(width, height):
            return False
        assert owner.image is not None  # sized above
        commands: list[Command] = [SetValue(variant, "image", crop_image(owner.image, crop))]
        for target in owner.targets or []:
            key = self.document.key(target)
            commands += [SetValue(key, "x", target.x - crop.left), SetValue(key, "y", target.y - crop.top)]
        if (cropped := cropped_match_area(owner.match_area, crop)) != owner.match_area:
            commands.append(SetValue(variant, "match_area", cropped))
        self.execute(Group(commands, "Crop image"))
        return True

    def variant_summary(self, key: int) -> VariantSummary:
        """Overrides and issues of a variant, as its row in the list shows them."""
        return summarize(self.document, key, self._issues)

    def variant_keys(self) -> list[int]:
        """Keys of the variants, in the order of the element."""
        return self._variant_keys()

    # Selection

    @property
    def selected_variant(self) -> int | None:
        return self._variant

    @property
    def selected_target(self) -> int | None:
        return self._target

    def request_match_area_edit(self) -> None:
        """Asks the canvas to edit the match area of the selected variant; neither a change nor a command."""
        self.match_area_edit_requested.emit()

    def request_text_edit(self) -> None:
        """Asks the centre to type the text of the selected text variant; neither a change nor a command."""
        self.text_edit_requested.emit()

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
        """Whether the Test applies the code overrides; Edit always shows them."""
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

    def _size(self, variant: int) -> tuple[int, int]:
        """Width and height of the image of a variant, which must have one."""
        image = self.document.get(variant).image
        assert image is not None, "an image variant with its image"
        height, width = image.shape[:2]
        return width, height

    def _variant_keys(self) -> list[int]:
        return [self.document.key(variant) for variant in self.document.variants]

    def _target_keys(self, variant: int | None) -> list[int]:
        if variant is None:
            return []
        return [self.document.key(target) for target in getattr(self.document.get(variant), "targets", None) or []]
