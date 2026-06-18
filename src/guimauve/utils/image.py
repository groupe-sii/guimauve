from typing import Optional

import cv2 as cv
import numpy as np


def diff_area(
    before: np.ndarray,
    after: np.ndarray,
    *,
    threshold: int = 30,
    dilation_px: int = 20,
    min_area: int = 200,
) -> Optional[tuple[int, int, int, int]]:
    """Returns the xywh bounding box of the largest changed region between two screenshots, or None."""
    if before.shape != after.shape:
        return None

    diff = cv.absdiff(before, after)
    gray = cv.cvtColor(diff, cv.COLOR_BGR2GRAY) if diff.ndim == 3 else diff
    _, mask = cv.threshold(gray, threshold, 255, cv.THRESH_BINARY)

    if dilation_px > 0:
        kernel = np.ones((dilation_px, dilation_px), np.uint8)
        mask = cv.dilate(mask, kernel)

    contours, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    best_rect = None
    best_area = 0
    for contour in contours:
        x, y, w, h = cv.boundingRect(contour)
        area = w * h
        if area >= min_area and area > best_area:
            best_rect = (x, y, w, h)
            best_area = area

    return best_rect


def similarity_index(image1: np.ndarray, image2: np.ndarray) -> float:
    """
    Computes a similarity index between two images based on pixel-wise differences.

    :param image1: The first image as a numpy array.
    :param image2: The second image as a numpy array.
    :return: A float between 0 and 1, where 1 indicates identical images.
    """
    if image1.shape != image2.shape:
        return 0.0

    img1 = image1.astype(np.uint8)
    img2 = image2.astype(np.uint8)
    diff = cv.absdiff(img1, img2)
    different_pixels = np.count_nonzero(diff)
    total_pixels = diff.size

    return 1.0 - different_pixels / total_pixels if total_pixels else 1.0
