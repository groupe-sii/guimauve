"""Descriptors of the editable properties.

Pydantic stays the source of truth for types, bounds and validation: a descriptor only adds what the
inspector needs on top of it (label, layout, display rules).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel

from guimauve.gui.common.fields import bounds
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, TextVariant

Values = Mapping[str, Any]
"""Resolved values of the element or variant being displayed, by field key."""

Rule = Callable[[Values], bool]

FIXED_POSITION_KEYS = ("x", "y", "rel_x", "rel_y")


class Level(Enum):
    """Where a field can be set."""

    ELEMENT = "element"
    IMAGE_VARIANT = "image_variant"
    TEXT_VARIANT = "text_variant"


_LEVEL_MODELS: dict[Level, type[BaseModel]] = {
    Level.ELEMENT: Element,
    Level.IMAGE_VARIANT: ImageVariant,
    Level.TEXT_VARIANT: TextVariant,
}


def always(values: Values) -> bool:
    return True


def enabled_by(flag: str) -> Rule:
    """Rule true when the given boolean field is on, e.g. the settings of a detection method."""
    return lambda values: bool(values.get(flag))


def no_fixed_position(values: Values) -> bool:
    """Rule true when no fixed position is set: detection settings have no effect otherwise."""
    return all(values.get(key) is None for key in FIXED_POSITION_KEYS)


@dataclass(frozen=True)
class FieldDescriptor:
    """An editable property, as shown in the inspector.

    :param key: Name of the field on the models.
    :param label: Label shown in the inspector.
    :param advanced: Shown in the collapsed "Advanced" group of its section.
    :param toggle: Switch that turns a detection method on, shown as a heading of its settings.
    :param visible: Hidden when false, e.g. the settings of a disabled detection method.
    :param effective: Disabled when false, because the field has no effect.
    :param relative: Field relative to the mouse on the same axis, edited with this one, e.g. rel_x for x.
    :param wide: Editor on its own line under the label, for an editor wider than the column of the editors.
    """

    key: str
    label: str
    advanced: bool = False
    toggle: bool = False
    visible: Rule = always
    effective: Rule = always
    relative: str | None = None
    wide: bool = False

    @property
    def levels(self) -> frozenset[Level]:
        """Levels where the field can be set, read from the models."""
        return frozenset(level for level, model in _LEVEL_MODELS.items() if self.key in model.model_fields)

    @property
    def bounds(self) -> tuple[Any, Any]:
        """Lower and upper bounds (ge, le) read from the models; None when unbounded."""
        return bounds(Element, self.key)

    @property
    def keys(self) -> tuple[str, ...]:
        """Fields of the models edited by this descriptor: the key, then the relative field if any."""
        return (self.key,) if self.relative is None else (self.key, self.relative)
