"""Reversible changes of the document.

Every change sets a value on a field of an owner: the element, a variant or a target. Lists of variants or targets
are replaced by a new list, never changed in place, so undo puts back the exact previous list with the same objects.
Trials go through commands too, on the trial layer of the document, so they can be undone.
"""

import copy
import dataclasses
from dataclasses import dataclass
from typing import Any, Protocol

from guimauve.gui.element_editor_next.state.document import Document

ELEMENT = None
"""Owner key of the element itself."""

_UNSET = object()
_ABSENT = object()  # previous state of a field that had no trial


class Command(Protocol):
    label: str

    def do(self, document: Document) -> None: ...

    def undo(self, document: Document) -> None: ...

    def merge(self, other: "Command") -> bool:
        """Absorbs a command run just after this one; returns False when they must stay separate."""
        ...


@dataclass
class SetValue:
    """Sets a field of the element, a variant or a target.

    :param owner: Key of the variant or target, or ELEMENT.
    :param field: Name of the field.
    :param value: New value; the document owns it from now on.
    :param label: Short description, e.g. for an undo menu.
    :param gesture: Identifier of a continuous edit (drag, slider): commands on the same field with the same
        gesture merge into one.
    """

    owner: int | None
    field: str
    value: Any
    label: str = ""
    gesture: int | None = None
    _previous: Any = dataclasses.field(default=_UNSET, init=False, repr=False)  # "field" is shadowed here

    def do(self, document: Document) -> None:
        target = _owner(document, self.owner)
        if self._previous is _UNSET:
            self._previous = getattr(target, self.field)
        setattr(target, self.field, self.value)

    def undo(self, document: Document) -> None:
        setattr(_owner(document, self.owner), self.field, self._previous)

    def merge(self, other: Command) -> bool:
        if self.gesture is None or not isinstance(other, SetValue):
            return False
        if (other.owner, other.field, other.gesture) != (self.owner, self.field, self.gesture):
            return False
        self.value = other.value
        return True


@dataclass
class Group:
    """Commands done and undone as one, e.g. a crop moving the image and its targets.

    :param gesture: Identifier of a continuous edit changing several fields, such as dragging a target: groups of
        the same gesture changing the same fields merge into one, each command into its own.
    """

    commands: list[Command]
    label: str = ""
    gesture: int | None = None

    def do(self, document: Document) -> None:
        for command in self.commands:
            command.do(document)

    def undo(self, document: Document) -> None:
        for command in reversed(self.commands):
            command.undo(document)

    def merge(self, other: Command) -> bool:
        if self.gesture is None or not isinstance(other, Group) or other.gesture != self.gesture:
            return False
        if [_changed(c) for c in self.commands] != [_changed(c) for c in other.commands]:
            return False
        merged = [mine.merge(theirs) for mine, theirs in zip(self.commands, other.commands, strict=True)]
        return all(merged)  # every command merged, none skipped


@dataclass
class SetTrial:
    """Sets the trial of a field of the element or a variant, or removes it when value is None.

    :param owner: Key of the variant, or ELEMENT.
    :param field: Name of the field.
    :param value: Tried value, or None to remove the trial.
    :param label: Short description, e.g. for an undo menu.
    :param gesture: Identifier of a continuous edit, as for SetValue.
    """

    owner: int | None
    field: str
    value: Any
    label: str = ""
    gesture: int | None = None
    _previous: Any = dataclasses.field(default=_UNSET, init=False, repr=False)  # "field" is shadowed here

    def do(self, document: Document) -> None:
        if self._previous is _UNSET:
            self._previous = _trials_of(document, self.owner).get(self.field, _ABSENT)
        _set_trial(document, self.owner, self.field, self.value)

    def undo(self, document: Document) -> None:
        _set_trial(document, self.owner, self.field, None if self._previous is _ABSENT else self._previous)

    def merge(self, other: Command) -> bool:
        if self.gesture is None or not isinstance(other, SetTrial):
            return False
        if (other.owner, other.field, other.gesture) != (self.owner, self.field, self.gesture):
            return False
        self.value = other.value
        return True


def apply_trials(document: Document, label: str = "Apply trials") -> Group:
    """Command writing the trials into the element and its variants, then removing them.

    Trials of a variant no longer in the element are removed without being applied.
    """
    present = {document.key(variant) for variant in document.variants}
    commands: list[Command] = []
    for owner, field, value in _trial_items(document):
        if owner is ELEMENT or owner in present:
            commands.append(SetValue(owner, field, copy.deepcopy(value)))
    return Group(commands + discard_trials(document).commands, label)


def discard_trials(document: Document, label: str = "Discard trials") -> Group:
    """Command removing every trial."""
    return Group([SetTrial(owner, field, None) for owner, field, _ in _trial_items(document)], label)


def insert(document: Document, owner: int | None, field: str, item: Any, index: int | None = None, label: str = ""):
    """Command adding a variant or target to a list, at the end by default."""
    items = _items(document, owner, field)
    items.insert(len(items) if index is None else index, item)
    return SetValue(owner, field, items, label)


def remove(document: Document, owner: int | None, field: str, key: int, label: str = ""):
    """Command removing a variant or target from a list; an empty list becomes None."""
    items = [item for item in _items(document, owner, field) if document.key(item) != key]
    return SetValue(owner, field, items or None, label)


def move(document: Document, owner: int | None, field: str, key: int, index: int, label: str = ""):
    """Command moving a variant or target to a new position in its list."""
    items = _items(document, owner, field)
    item = next(item for item in items if document.key(item) == key)
    items.remove(item)
    items.insert(index, item)
    return SetValue(owner, field, items, label)


def _changed(command: Command) -> tuple[type, Any, Any]:
    """What a command changes, to tell whether two groups can merge."""
    return type(command), getattr(command, "owner", None), getattr(command, "field", None)


def _owner(document: Document, key: int | None) -> Any:
    return document.element if key is ELEMENT else document.get(key)


def _items(document: Document, owner: int | None, field: str) -> list:
    return list(getattr(_owner(document, owner), field) or [])


def _trials_of(document: Document, owner: int | None) -> dict[str, Any]:
    trials = document.trials
    return trials.element if owner is ELEMENT else trials.variants.get(owner, {})


def _set_trial(document: Document, owner: int | None, field: str, value: Any) -> None:
    trials = document.trials
    values = trials.element if owner is ELEMENT else trials.variants.setdefault(owner, {})
    if value is None:
        values.pop(field, None)
    else:
        values[field] = value
    if owner is not ELEMENT and not values:
        del trials.variants[owner]


def _trial_items(document: Document) -> list[tuple[int | None, str, Any]]:
    trials = document.trials
    items: list[tuple[int | None, str, Any]] = [(ELEMENT, f, v) for f, v in trials.element.items()]
    items += [(key, f, v) for key, values in trials.variants.items() for f, v in values.items()]
    return items
