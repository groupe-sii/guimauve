"""Geometry of an image variant: points and areas kept inside the image, and what a crop keeps; without Qt.

Areas follow the model: left and top included, right and bottom excluded.
"""

import numpy as np

from guimauve.models.area import Area
from guimauve.models.variant import Target


def clamp_point(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """Nearest pixel of an image of this size."""
    return min(max(x, 0), width - 1), min(max(y, 0), height - 1)


def intersect(area: Area, other: Area) -> Area | None:
    """Common part of two areas; None when they do not overlap."""
    left, top = max(area.left, other.left), max(area.top, other.top)
    right, bottom = min(area.right, other.right), min(area.bottom, other.bottom)
    if left >= right or top >= bottom:
        return None
    return Area(left=left, top=top, right=right, bottom=bottom)


def whole(width: int, height: int) -> Area:
    """Area of a whole image of this size."""
    return Area(left=0, top=0, right=width, bottom=height)


def match_area(area: Area | None, width: int, height: int) -> Area | None:
    """Match area as stored: clipped to the image, None for the whole image or when nothing is left."""
    clipped = None if area is None else intersect(area, whole(width, height))
    if clipped is None or clipped.as_ltrb() == (0, 0, width, height):
        return None
    return clipped


def is_inside(target: Target, area: Area) -> bool:
    return area.left <= target.x < area.right and area.top <= target.y < area.bottom


def removed_by_crop(targets: list[Target] | None, crop: Area) -> list[Target]:
    """Targets a crop would remove, being outside of it."""
    return [target for target in targets or [] if not is_inside(target, crop)]


def crop_image(image: np.ndarray, crop: Area) -> np.ndarray:
    """New array holding the cropped part of the image."""
    return image[crop.top : crop.bottom, crop.left : crop.right].copy()


def cropped_match_area(area: Area | None, crop: Area) -> Area | None:
    """Match area once the image is cropped: clipped to the crop and moved with it."""
    kept = None if area is None else intersect(area, crop)
    if kept is None:
        return None
    moved = Area(
        left=kept.left - crop.left, top=kept.top - crop.top, right=kept.right - crop.left, bottom=kept.bottom - crop.top
    )
    return match_area(moved, crop.width, crop.height)
