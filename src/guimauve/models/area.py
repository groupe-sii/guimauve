from typing import Optional

from pydantic import field_validator, model_validator

from guimauve.models.base import Model, raise_if_any, strict_only
from guimauve.utils.screen import get_screen_size


class Area(Model):
    top: int
    left: int
    right: int
    bottom: int

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

    @field_validator("top", "bottom", mode="after")
    @classmethod
    @strict_only
    def _vertical_within_screen(cls, v, info):
        _, height = get_screen_size()
        if not 0 <= v <= height:
            raise ValueError(f"must be between 0 and {height}")
        return v

    @field_validator("left", "right", mode="after")
    @classmethod
    @strict_only
    def _horizontal_within_screen(cls, v, info):
        width, _ = get_screen_size()
        if not 0 <= v <= width:
            raise ValueError(f"must be between 0 and {width}")
        return v

    def _check_top_before_bottom(self) -> Optional[str]:
        if self.top >= self.bottom:
            return "top must be less than bottom"
        return None

    def _check_left_before_right(self) -> Optional[str]:
        if self.left >= self.right:
            return "left must be less than right"
        return None

    @model_validator(mode="after")
    @strict_only
    def _ordering(self, info):
        raise_if_any(self._check_top_before_bottom(), self._check_left_before_right())
        return self
