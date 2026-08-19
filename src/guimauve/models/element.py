from typing import Optional

from pydantic import PrivateAttr, field_validator, model_validator

from guimauve.models.base import join_natural, raise_if_any, strict_only
from guimauve.models.params import ElementParams, ImageParams, LocateParams, MatchParams, MouseParams, TextParams
from guimauve.models.variant import ImageVariant, VariantUnion


class Element(ElementParams, LocateParams, MouseParams, ImageParams, TextParams, MatchParams):
    name: Optional[str] = None
    data_file: Optional[str] = None

    x: Optional[int] = None
    y: Optional[int] = None
    rel_x: Optional[int] = None
    rel_y: Optional[int] = None

    variants: Optional[list[VariantUnion]] = None

    # Runtime-only flag (not a model field): True for a placeholder Element not yet in a data file.
    _is_new: bool = PrivateAttr(default=False)

    def has_coordinates(self) -> bool:
        return any(coord is not None for coord in (self.x, self.y, self.rel_x, self.rel_y))

    def resolve_coordinates(self, mouse_x: int, mouse_y: int) -> Optional[tuple[int, int]]:
        res_x = self.x if self.x is not None else (mouse_x + (self.rel_x or 0))
        res_y = self.y if self.y is not None else (mouse_y + (self.rel_y or 0))

        return res_x, res_y

    @field_validator("name", mode="after")
    @classmethod
    @strict_only
    def _name_not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v

    def _check_x_conflict(self) -> Optional[str]:
        if self.x is not None and self.rel_x is not None:
            return "cannot have an absolute and a relative X"
        return None

    def _check_y_conflict(self) -> Optional[str]:
        if self.y is not None and self.rel_y is not None:
            return "cannot have an absolute and a relative Y"
        return None

    def _check_has_coordinates_or_variant(self) -> Optional[str]:
        if not self.has_coordinates() and not self.variants:
            return "must have at least coordinates or one variant"
        return None

    def _check_target_defined_in_variants(self) -> Optional[str]:
        if self.target is None or isinstance(self.target, (tuple, list)):
            return None

        missing = [
            variant.name
            for variant in self.variants or []
            if isinstance(variant, ImageVariant)
            and not any(self.target == target.name for target in variant.targets or [])
        ]
        if missing:
            plural = "variants" if len(missing) > 1 else "variant"
            return f"target '{self.target}' is not defined in {plural} {join_natural(missing)}"
        return None

    @model_validator(mode="after")
    @strict_only
    def _cross_field_rules(self, info):
        raise_if_any(
            self._check_x_conflict(),
            self._check_y_conflict(),
            self._check_has_coordinates_or_variant(),
            self._check_target_defined_in_variants(),
        )
        return self
