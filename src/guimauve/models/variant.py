from typing import Annotated, Optional, Union

import numpy as np
from pydantic import Discriminator, Tag, field_validator

from guimauve.models.area import Area
from guimauve.models.base import Model, strict_only
from guimauve.models.params import ImageParams, LocateParams, MatchParams, MouseParams, TextParams


class Variant(LocateParams, MouseParams, MatchParams):
    name: str


class Target(Model):
    name: str
    x: int
    y: int


class ImageVariant(Variant, ImageParams):
    path: Optional[str] = None
    image: Optional[np.ndarray] = None
    targets: Optional[list[Target]] = None
    default_target: Optional[str] = None
    match_area: Optional[Area] = None

    @field_validator("path", mode="after")
    @classmethod
    @strict_only
    def _path_not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class TextVariant(Variant, TextParams):
    text: Optional[str] = None

    @field_validator("text", mode="after")
    @classmethod
    @strict_only
    def _text_not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


def _variant_kind(v):
    """Discriminate ImageVariant vs TextVariant by structure, not Pydantic's smart-union scoring.

    Smart union picks the member with fewer errors, but our strict-only rules (Bounds, "must not
    be empty") only raise in strict context — so a real ImageVariant with a strict violation could
    silently score better as a TextVariant (which ignores unrelated keys) and get reclassified.
    """
    if isinstance(v, ImageVariant):
        return "image"
    if isinstance(v, TextVariant):
        return "text"
    if isinstance(v, dict):
        if any(key in v for key in ("path", "image", "targets", "default_target", "match_area")):
            return "image"
        if "text" in v:
            return "text"
    return "image"  # ambiguous (e.g. only `name` present) — matches the old tie-break default


VariantUnion = Annotated[
    Union[Annotated[ImageVariant, Tag("image")], Annotated[TextVariant, Tag("text")]],
    Discriminator(_variant_kind),
]
