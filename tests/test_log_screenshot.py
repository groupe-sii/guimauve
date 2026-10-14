import cv2 as cv
import numpy as np

from guimauve.detection.detector import Box, Match, Point
from guimauve.log_screenshot import log_screenshot
from guimauve.models.parameters import Screenshot

BLUE = (0, 0, 255)  # (255, 0, 0) drawn in RGB, read back in BGR


def saved_image(folder):
    [path] = folder.glob("*.png")
    return cv.imread(str(path))


def test_drawings_are_moved_from_desktop_to_screen_coordinates(tmp_path):
    """The screen logged starts at x = -1280: desktop points are drawn relative to it."""
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    match = Match(
        box=Box(Point(-1250, 40), Point(-1230, 40), Point(-1230, 60), Point(-1250, 60)),
        target=Point(-1240, 50),
        confidence=1.0,
    )
    log_screenshot(
        Screenshot(enable=True, folder=tmp_path),
        "locate",
        (),
        {},
        None,
        lambda: (image, (-1280, 0)),
        Point(-1270, 20),
        [match],
    )
    saved = saved_image(tmp_path)
    assert tuple(saved[20, 10]) == BLUE  # mouse
    assert tuple(saved[50, 40]) == BLUE  # match target
    assert tuple(saved[40, 30]) == BLUE  # match box corner
