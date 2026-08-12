from typing import Optional, Union

from sugar import UNDEFINED

from guimauve.models.params import ElementParams, ImageParams, LocateParams, MatchParams, MouseParams, TextParams
from guimauve.models.variant import ImageVariant, TextVariant


class Element(ElementParams, LocateParams, MouseParams, ImageParams, TextParams, MatchParams):
    name: Optional[str]
    data_file: Optional[str]

    x: Optional[int]
    y: Optional[int]
    rel_x: Optional[int]
    rel_y: Optional[int]

    variants: Optional[list[Union[ImageVariant, TextVariant]]]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._is_new = False

    def has_coordinates(self) -> bool:
        return any(coord not in (None, UNDEFINED) for coord in (self.x, self.y, self.rel_x, self.rel_y))

    def resolve_coordinates(self, mouse_x: int, mouse_y: int) -> Optional[tuple[int, int]]:
        res_x = self.x if self.x not in (None, UNDEFINED) else (mouse_x + (self.rel_x or 0))
        res_y = self.y if self.y not in (None, UNDEFINED) else (mouse_y + (self.rel_y or 0))

        return res_x, res_y

    def validate_name(self):
        if not self.name or self.name.strip() == "":
            yield "must be not empty"

    def validate_target(self):
        if isinstance(self.target, (tuple, list)):
            return

        missing = []
        for variant in self.variants or []:
            if isinstance(variant, ImageVariant):
                if not any(self.target == target.name for target in variant.targets or []):
                    missing.append(variant.name)

        if missing:
            yield f"target '{self.target}' is not defined in the variant(s) {missing}"

    def full_validate(self):
        if self.x not in (None, UNDEFINED) and self.rel_x not in (None, UNDEFINED):
            yield "cannot have an absolute and a relative X"

        if self.y not in (None, UNDEFINED) and self.rel_y not in (None, UNDEFINED):
            yield "cannot have an absolute and a relative Y"

        if not self.has_coordinates() and not self.variants:
            yield "must have at least coordinates or one variant"
