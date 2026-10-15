"""Reversible changes of the document.

Every change sets a value on a field of an owner: the element, a variant or a target. Lists of variants or targets
are replaced by a new list, never changed in place, so undo puts back the exact previous list with the same objects.
"""

import dataclasses
from dataclasses import dataclass
from typing import Any, Protocol

from guimauve.gui.element_editor_next.state.document import Document

ELEMENT = None
"""Owner key of the element itself."""

_UNSET = object()


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
    """Commands done and undone as one, e.g. a crop moving the image and its targets."""

    commands: list[Command]
    label: str = ""

    def do(self, document: Document) -> None:
        for command in self.commands:
            command.do(document)

    def undo(self, document: Document) -> None:
        for command in reversed(self.commands):
            command.undo(document)

    def merge(self, other: Command) -> bool:
        return False


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


def _owner(document: Document, key: int | None) -> Any:
    return document.element if key is ELEMENT else document.get(key)


def _items(document: Document, owner: int | None, field: str) -> list:
    return list(getattr(_owner(document, owner), field) or [])
