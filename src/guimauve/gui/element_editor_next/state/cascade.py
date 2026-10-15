"""Resolution of property values across the cascade.

From the weakest to the strongest layer: default, element, code, element trial, variant, variant trial. A variant
value wins over the code, as in Controller._update; a trial wins over the layer of its own level.
"""

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from guimauve.gui.element_editor_next.state.document import Document
from guimauve.models.element import Element
from guimauve.models.parameters import DefaultProperties
from guimauve.models.variant import Variant


class Source(Enum):
    """Layer a value comes from, declared from the weakest to the strongest."""

    DEFAULT = "default"
    ELEMENT = "element"
    CODE = "code"
    ELEMENT_TRIAL = "element_trial"
    VARIANT = "variant"
    VARIANT_TRIAL = "variant_trial"


@dataclass
class Trials:
    """Values tried in Test mode, not yet applied to the document.

    :param element: Tried values of the element, by field name.
    :param variants: Tried values of each variant, by variant key then field name.
    """

    element: dict[str, Any] = field(default_factory=dict)
    variants: dict[int, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class Resolution:
    """Value of a field and where it comes from.

    :param value: Value applied; None when no layer defines it.
    :param source: Layer of the applied value; None when no layer defines it.
    :param layers: Value of every layer that defines it, from the weakest to the strongest.
    """

    value: Any
    source: Source | None
    layers: dict[Source, Any]


def resolve(
    key: str,
    document: Document,
    default: DefaultProperties,
    variant: Variant | None = None,
    trials: Trials | None = None,
    include_code: bool = True,
) -> Resolution:
    """Resolves one field, for the element or for one of its variants."""
    layers: dict[Source, Any] = {}
    for source, values in _layers(document, default, variant, trials or Trials(), include_code):
        if key in values and (value := values[key]) is not None:
            layers[source] = value

    if not layers:
        return Resolution(None, None, {})
    source = list(layers)[-1]
    return Resolution(layers[source], source, layers)


def resolve_element(
    document: Document,
    default: DefaultProperties,
    trials: Trials | None = None,
    include_code: bool = True,
) -> Element:
    """Returns the element as the controller locates it, with every variant resolved."""
    trials = trials or Trials()
    element = _resolve_base(document, default, trials, include_code)
    variants: list = [_resolve_variant(document, element, variant, trials) for variant in document.variants]
    element.variants = variants
    return element


def resolve_variant(
    document: Document,
    default: DefaultProperties,
    variant: Variant,
    trials: Trials | None = None,
    include_code: bool = True,
) -> Variant:
    """Returns one variant as the controller locates it."""
    trials = trials or Trials()
    return _resolve_variant(document, _resolve_base(document, default, trials, include_code), variant, trials)


def _layers(document, default, variant, trials, include_code):
    yield Source.DEFAULT, _fields(default)
    yield Source.ELEMENT, _fields(document.element)
    if include_code:
        yield Source.CODE, document.code_overrides
    yield Source.ELEMENT_TRIAL, trials.element
    if variant is not None:
        own = _fields(variant)
        tried = trials.variants.get(document.key(variant), {})
        yield Source.VARIANT, own
        # A field missing on the variant type stays an element field, even when tried on the variant.
        yield Source.VARIANT_TRIAL, {key: value for key, value in tried.items() if key in own}


def _fields(model) -> Mapping[str, Any]:
    return {name: getattr(model, name) for name in type(model).model_fields}


def _resolve_base(document, default, trials, include_code) -> Element:
    element = document.element.model_copy(update={"variants": None})
    _apply(element, document.code_overrides if include_code else {})
    _apply(element, trials.element)
    return element.update(default, overwrite=False)


def _resolve_variant(document, element, variant, trials) -> Variant:
    resolved = variant.model_copy()
    _apply(resolved, trials.variants.get(document.key(variant), {}))
    return resolved.update(element, exclude={"name"}, overwrite=False)


def _apply(model, values: Mapping[str, Any]) -> None:
    for name, value in values.items():
        if name in type(model).model_fields and value is not None:
            setattr(model, name, copy.deepcopy(value))
