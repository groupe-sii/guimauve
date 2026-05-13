import cv2 as cv
import numpy as np


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
