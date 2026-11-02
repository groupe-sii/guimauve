"""Working copy of the element edited during a session."""

from dataclasses import dataclass, field
from itertools import count
from typing import Any

from guimauve.models.element import Element
from guimauve.models.model import Model
from guimauve.models.variant import ImageVariant, Target, Variant


@dataclass
class Trials:
    """Values tried in Test mode, kept apart from the element and never saved.

    :param element: Tried values of the element, by field name.
    :param variants: Tried values of each variant, by variant key then field name.
    """

    element: dict[str, Any] = field(default_factory=dict)
    variants: dict[int, dict[str, Any]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.element and not any(self.variants.values())


class Document:
    """Working copy of an element, with stable keys for its variants and targets.

    The element received is never modified. Variants and targets are edited in place and never replaced, so
    their key stays valid for the whole session, whatever their name.

    :param element: Element to edit, without the overrides set in the code.
    :param code_overrides: Values set in the code for this call, by field name; kept apart from the element.

    The trials are kept apart too: they change neither is_modified() nor the saved element.
    """

    def __init__(self, element: Element, code_overrides: dict[str, Any] | None = None):
        self.element = element.model_copy(deep=True)
        self.code_overrides = dict(code_overrides or {})
        self.trials = Trials()

        self._counter = count(1)
        self._keys: dict[int, int] = {}  # id(obj) -> key
        self._objects: dict[int, Model] = {}  # key -> obj; also keeps every obj alive, so id() is never reused

        for variant in self.variants:
            self.key(variant)
            if isinstance(variant, ImageVariant):
                _load_image(variant)
                for target in variant.targets or []:
                    self.key(target)

        self._opening = self._snapshot()

    @property
    def variants(self) -> list[Variant]:
        return list(self.element.variants or [])

    def key(self, obj: Variant | Target) -> int:
        """Returns the key of a variant or target, giving a new one to an object not seen yet."""
        if (key := self._keys.get(id(obj))) is None:
            key = next(self._counter)
            self._keys[id(obj)] = key
            self._objects[key] = obj
        return key

    def get(self, key: int) -> Any:
        """Returns the variant or target with the given key, even when it is no longer in the element."""
        return self._objects[key]

    def is_modified(self) -> bool:
        """Compares the element with its opening state; undoing every change makes it unmodified again."""
        data, images = self._snapshot()
        opening_data, opening_images = self._opening
        if data != opening_data or images.keys() != opening_images.keys():
            return True
        # Images are compared by identity: a change always sets a new array, undo puts the previous one back.
        return any(images[key] is not opening_images[key] for key in images)

    def _snapshot(self) -> tuple[tuple[str, dict], dict[int, Any]]:
        data = (self.element.name, self.element.to_dict(json_mode=True))
        images = {self.key(v): v.image for v in self.variants if isinstance(v, ImageVariant)}
        return data, images


def _load_image(variant: ImageVariant) -> None:
    """Loads the image of a variant in memory; a missing file is left to the validation."""
    if variant.image is not None or variant.path is None:
        return
    try:
        variant.load()
    except ValueError:
        variant.image = None
