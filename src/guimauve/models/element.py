from typing import Optional

from pydantic import PrivateAttr, field_validator, model_validator
from pydantic_core import PydanticCustomError

from guimauve.models.model import check_all
from guimauve.models.properties import (
    ElementProperties,
    ImageProperties,
    LocateProperties,
    MatchProperties,
    MouseProperties,
    TextProperties,
)
from guimauve.models.variant import ImageVariant, VariantUnion


class Element(ElementProperties, LocateProperties, MouseProperties, ImageProperties, TextProperties, MatchProperties):
    name: Optional[str] = None

    x: Optional[int] = None
    y: Optional[int] = None
    rel_x: Optional[int] = None
    rel_y: Optional[int] = None

    variants: Optional[dict[str, VariantUnion]] = None

    _alias: Optional[str] = PrivateAttr(default=None)
    _is_new: bool = PrivateAttr(default=False)
    _resolved: bool = PrivateAttr(default=False)

    @property
    def alias(self) -> Optional[str]:
        return self._alias

    @property
    def is_new(self) -> bool:
        return self._is_new

    @property
    def resolved(self) -> bool:
        return self._resolved

    def has_coordinates(self) -> bool:
        return any(coord is not None for coord in (self.x, self.y, self.rel_x, self.rel_y))

    def resolve_coordinates(self, mouse_x: int, mouse_y: int) -> Optional[tuple[int, int]]:
        res_x = self.x if self.x is not None else (mouse_x + (self.rel_x or 0))
        res_y = self.y if self.y is not None else (mouse_y + (self.rel_y or 0))

        return res_x, res_y

    @field_validator("name", mode="after")
    @classmethod
    def _name_not_empty(cls, v):
        if v is not None and not v.strip():
            raise PydanticCustomError("empty", "Must not be empty")
        return v

    @model_validator(mode="after")
    def _model_checks(self):
        check_all(
            self._check_x_conflict,
            self._check_y_conflict,
            self._check_has_coordinates_or_variant,
            self._check_target_defined_in_variants,
        )
        return self

    def _check_x_conflict(self):
        if self.x is not None and self.rel_x is not None:
            raise PydanticCustomError(
                "coordinate_conflict",
                "Cannot have an absolute and a relative X",
                {"axis": "x"},
            )

    def _check_y_conflict(self):
        if self.y is not None and self.rel_y is not None:
            raise PydanticCustomError(
                "coordinate_conflict",
                "Cannot have an absolute and a relative Y",
                {"axis": "y"},
            )

    def _check_has_coordinates_or_variant(self):
        if not self.has_coordinates() and not self.variants:
            raise PydanticCustomError(
                "no_locator",
                "Must have at least coordinates or one variant",
            )

    def _check_target_defined_in_variants(self):
        if self.target is None or isinstance(self.target, (tuple, list)):
            return

        missing = [
            name
            for name, variant in (self.variants or {}).items()
            if isinstance(variant, ImageVariant)
            and not any(self.target == target.name for target in variant.targets or [])
        ]
        if missing:
            plural = "s" if len(missing) > 1 else ""
            raise PydanticCustomError(
                "target_not_found",
                "target '{target}' is not defined in variant{plural} {names}",
                {"target": self.target, "plural": plural, "names": ", ".join(missing), "missing": missing},
            )
