from pathlib import Path
from typing import Annotated, Optional, Union

import cv2 as cv
import numpy as np
from pydantic import ConfigDict, Discriminator, Field, Tag, field_validator, model_validator
from pydantic_core import PydanticCustomError

from guimauve.models.area import Area
from guimauve.models.model import Model
from guimauve.models.properties import (
    ImageProperties,
    LocateProperties,
    MatchProperties,
    MouseProperties,
    TextProperties,
)


class Variant(LocateProperties, MouseProperties, MatchProperties):
    name: Optional[str] = None

    @field_validator("name", mode="after")
    @classmethod
    def _name_not_empty(cls, v):
        if v is not None and not v.strip():
            raise PydanticCustomError("empty", "Must not be empty")
        return v


class Target(Model):
    name: Optional[str] = None
    x: int
    y: int
    __hash__ = object.__hash__

    @field_validator("name", mode="after")
    @classmethod
    def _name_not_empty(cls, v):
        if v is not None and not v.strip():
            raise PydanticCustomError("empty", "Must not be empty")
        return v


class ImageVariant(Variant, ImageProperties):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Optional[Path] = None
    image: Optional[np.ndarray] = Field(default=None, exclude=True)
    targets: Optional[list[Target]] = None
    default_target: Optional[str] = None
    match_area: Optional[Area] = None

    def load(self):
        if self.image is None:
            image = cv.imread(str(self.path))
            if image is None:
                raise ValueError(f"could not read image at {self.path}")
            self.image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
        return self

    @field_validator("path", mode="after")
    @classmethod
    def _path_exists(cls, v):
        if v is not None and not v.is_file():
            raise PydanticCustomError("file_not_found", "File does not exist", {"path": str(v)})
        return v

    @model_validator(mode="after")
    def _require_path(self):
        if self.path is None:
            raise PydanticCustomError("path_missing", "an image variant must have a path")
        return self


class TextVariant(Variant, TextProperties):
    text: str

    @field_validator("text", mode="after")
    @classmethod
    def _text_not_empty(cls, v):
        if not v.strip():
            raise PydanticCustomError("empty", "Must not be empty")
        return v


def _variant_kind(v):
    """Discriminate ImageVariant vs TextVariant by structure, not Pydantic's smart-union scoring."""
    if isinstance(v, ImageVariant):
        return "image"
    if isinstance(v, TextVariant):
        return "text"
    if isinstance(v, dict):
        if any(key in v for key in ("path", "image", "targets", "default_target", "match_area")):
            return "image"
        if "text" in v:
            return "text"
    return "image"


VariantUnion = Annotated[
    Union[Annotated[ImageVariant, Tag("image")], Annotated[TextVariant, Tag("text")]],
    Discriminator(_variant_kind),
]
