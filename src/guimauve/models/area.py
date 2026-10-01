from pydantic import NonNegativeInt, model_validator
from pydantic_core import PydanticCustomError

from guimauve.models.model import Model, check_all


class Area(Model):
    top: NonNegativeInt
    left: NonNegativeInt
    right: NonNegativeInt
    bottom: NonNegativeInt

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def tl(self) -> tuple[int, int]:
        return self.left, self.top

    @property
    def tr(self) -> tuple[int, int]:
        return self.right, self.top

    @property
    def br(self) -> tuple[int, int]:
        return self.right, self.bottom

    @property
    def bl(self) -> tuple[int, int]:
        return self.left, self.bottom

    def as_xywh(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.width, self.height

    def as_ltrb(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom

    @model_validator(mode="after")
    def _model_checks(self):
        check_all(self._check_top_before_bottom, self._check_left_before_right)
        return self

    def _check_top_before_bottom(self):
        if self.top >= self.bottom:
            raise PydanticCustomError(
                "invalid_order",
                "'top' should be less than 'bottom'",
                {"axis": "vertical"},
            )

    def _check_left_before_right(self):
        if self.left >= self.right:
            raise PydanticCustomError(
                "invalid_order",
                "'left' should be less than 'right'",
                {"axis": "horizontal"},
            )
