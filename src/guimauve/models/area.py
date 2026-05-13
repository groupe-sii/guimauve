from sugar import Schema

from guimauve.utils.screen import get_screen_size


class Area(Schema):
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

    def as_xywh(self):
        return self.left, self.top, self.width, self.height

    def as_ltrb(self):
        return self.left, self.top, self.right, self.bottom

    def full_validate(self):
        width, height = get_screen_size()

        if not 0 <= self.top <= height:
            yield "top", f"must be between 0 and {height}"
        if not 0 <= self.left <= width:
            yield "left", f"must be between 0 and {width}"
        if not 0 <= self.right <= width:
            yield "right", f"must be between 0 and {width}"
        if not 0 <= self.bottom <= height:
            yield "bottom", f"must be between 0 and {height}"

        if self.top >= self.bottom:
            yield "top must be less than bottom"
        if self.left >= self.right:
            yield "left must be less than right"
