"""Conversions between the images of the models, as RGB arrays, and Qt or files."""

from pathlib import Path

import cv2 as cv
import numpy as np
from PySide6.QtGui import QImage

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
"""Filter of the file dialogs that import an image."""


def to_qimage(array: np.ndarray) -> QImage:
    """Copy of an RGB or grayscale array as a QImage, which no longer depends on the array."""
    array = np.ascontiguousarray(array)
    height, width = array.shape[:2]
    if array.ndim == 2:
        return QImage(array.data, width, height, array.strides[0], QImage.Format.Format_Grayscale8).copy()
    return QImage(array.data, width, height, array.strides[0], QImage.Format.Format_RGB888).copy()


def read_image(path: Path) -> np.ndarray | None:
    """Reads an image file as RGB, as ImageVariant.load does; None when it cannot be read.

    The bytes are decoded from memory, since cv.imread fails on paths outside the system code page on Windows.
    """
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except OSError:
        return None
    image = cv.imdecode(data, cv.IMREAD_COLOR)
    return None if image is None else cv.cvtColor(image, cv.COLOR_BGR2RGB)
