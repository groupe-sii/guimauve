"""Thumbnails of the image variants, computed once per image and match area."""

from dataclasses import dataclass

import cv2 as cv
import numpy as np
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage

from guimauve.gui.element_editor_next.services.images import to_qimage
from guimauve.models.area import Area
from guimauve.models.variant import ImageVariant

MAX_SCALE = 2.0
"""A small image is enlarged at most twice, so its pixels stay readable."""


def fit(width: int, height: int, box: QSize) -> QSize:
    """Size of an image scaled into the box, keeping its proportions and enlarged at most MAX_SCALE times."""
    scale = min(box.width() / width, box.height() / height, MAX_SCALE)
    return QSize(max(1, round(width * scale)), max(1, round(height * scale)))


def crop(image: np.ndarray, area: Area | None) -> np.ndarray:
    """Part of the image inside the area, clipped to the image; the whole image without area or when empty."""
    if area is None:
        return image
    height, width = image.shape[:2]
    left, top = min(area.left, width), min(area.top, height)
    right, bottom = min(area.right, width), min(area.bottom, height)
    return image if right <= left or bottom <= top else image[top:bottom, left:right]


def thumbnail(image: np.ndarray, area: Area | None, box: QSize, ratio: float = 1.0) -> QImage:
    """The match area of the image, or the whole image, scaled into the box at the device pixel ratio."""
    part = crop(image, area)
    height, width = part.shape[:2]
    size = fit(width, height, box) * ratio
    interpolation = cv.INTER_AREA if size.width() < width else cv.INTER_LINEAR
    result = to_qimage(cv.resize(part, (size.width(), size.height()), interpolation=interpolation))
    result.setDevicePixelRatio(ratio)
    return result


@dataclass(frozen=True)
class _Entry:
    image: np.ndarray  # kept to compare by identity: a new image is always a new array
    area: tuple[int, int, int, int] | None
    ratio: float
    thumbnail: QImage


class ThumbnailCache:
    """Thumbnails of one size by variant key, computed again only when the image or the match area changes.

    :param box: Size the thumbnails fit in, in logical pixels.
    """

    def __init__(self, box: QSize):
        self._box = box
        self._entries: dict[int, _Entry] = {}

    def get(self, key: int, variant: ImageVariant, ratio: float = 1.0) -> QImage | None:
        """Thumbnail of the variant; None when it has no image."""
        image = variant.image
        if image is None:
            self._entries.pop(key, None)
            return None
        area = variant.match_area.as_ltrb() if variant.match_area is not None else None
        entry = self._entries.get(key)
        if entry is None or entry.image is not image or entry.area != area or entry.ratio != ratio:
            entry = _Entry(image, area, ratio, thumbnail(image, variant.match_area, self._box, ratio))
            self._entries[key] = entry
        return entry.thumbnail

    def keep(self, keys: set[int]) -> None:
        """Forgets the thumbnails of the variants no longer in the list."""
        self._entries = {key: entry for key, entry in self._entries.items() if key in keys}
