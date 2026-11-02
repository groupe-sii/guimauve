"""Rectangle edited on the image, for the match area or a crop; without Qt.

Edges lie between pixels: left and top included, right and bottom excluded, as in the model's Area. The rectangle
stays inside the image and keeps at least one pixel.
"""

from dataclasses import dataclass
from enum import Enum

from guimauve.models.area import Area


@dataclass(frozen=True)
class Region:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def area(self) -> Area:
        return Area(left=self.left, top=self.top, right=self.right, bottom=self.bottom)

    @staticmethod
    def of(area: Area) -> "Region":
        return Region(area.left, area.top, area.right, area.bottom)

    @staticmethod
    def whole(width: int, height: int) -> "Region":
        return Region(0, 0, width, height)


class Grip(Enum):
    """Part of the rectangle grabbed: a handle moves its edges, the inside moves it all, the outside draws anew."""

    TOP_LEFT = (-1, -1)
    TOP = (0, -1)
    TOP_RIGHT = (1, -1)
    RIGHT = (1, 0)
    BOTTOM_RIGHT = (1, 1)
    BOTTOM = (0, 1)
    BOTTOM_LEFT = (-1, 1)
    LEFT = (-1, 0)
    INSIDE = (0, 0)
    OUTSIDE = None


HANDLES = [grip for grip in Grip if grip not in (Grip.INSIDE, Grip.OUTSIDE)]


def handle_points(region: Region) -> dict[Grip, tuple[float, float]]:
    """Position of each handle, on the edges and corners, in image coordinates."""
    middle_x, middle_y = (region.left + region.right) / 2, (region.top + region.bottom) / 2
    xs = {-1: float(region.left), 0: middle_x, 1: float(region.right)}
    ys = {-1: float(region.top), 0: middle_y, 1: float(region.bottom)}
    return {grip: (xs[grip.value[0]], ys[grip.value[1]]) for grip in HANDLES}


def resize(region: Region, grip: Grip, x: float, y: float, width: int, height: int) -> Region:
    """Moves the edges of a handle to a point of the image, rounded between pixels; one pixel stays at least."""
    horizontal, vertical = grip.value or (0, 0)
    left, top, right, bottom = region.left, region.top, region.right, region.bottom
    if horizontal < 0:
        left = min(max(round(x), 0), right - 1)
    elif horizontal > 0:
        right = max(min(round(x), width), left + 1)
    if vertical < 0:
        top = min(max(round(y), 0), bottom - 1)
    elif vertical > 0:
        bottom = max(min(round(y), height), top + 1)
    return Region(left, top, right, bottom)


def move(region: Region, dx: int, dy: int, width: int, height: int) -> Region:
    """Moves the rectangle by whole pixels, stopping at the borders of the image."""
    dx = min(max(dx, -region.left), width - region.right)
    dy = min(max(dy, -region.top), height - region.bottom)
    return Region(region.left + dx, region.top + dy, region.right + dx, region.bottom + dy)


def drawn(start: tuple[int, int], end: tuple[int, int], width: int, height: int) -> Region:
    """Rectangle covering two pixels and those between them, inside the image."""

    def clamp(value: int, size: int) -> int:
        return min(max(value, 0), size - 1)

    (x0, y0), (x1, y1) = start, end
    x0, x1 = clamp(x0, width), clamp(x1, width)
    y0, y1 = clamp(y0, height), clamp(y1, height)
    return Region(min(x0, x1), min(y0, y1), max(x0, x1) + 1, max(y0, y1) + 1)
