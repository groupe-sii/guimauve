import cv2 as cv
import numpy as np

from guimauve.gui.element_editor_next.services import read_image, to_qimage


def test_to_qimage_copies_the_rgb_pixels(qapp):
    array = np.zeros((2, 3, 3), np.uint8)
    array[1, 2] = (10, 20, 30)

    image = to_qimage(array)
    array[1, 2] = 0

    assert (image.width(), image.height()) == (3, 2)
    assert image.pixelColor(2, 1).getRgb()[:3] == (10, 20, 30)


def test_to_qimage_of_a_view(qapp):
    array = np.zeros((4, 4, 3), np.uint8)
    array[1:3, 1:3] = 200

    image = to_qimage(array[1:3, 1:3])

    assert image.pixelColor(1, 1).red() == 200


def test_read_image_as_rgb(tmp_path):
    path = tmp_path / "écran.png"  # outside ASCII, as on a French Windows
    cv.imencode(".png", np.full((2, 2, 3), (255, 0, 0), np.uint8))[1].tofile(path)  # blue, in BGR

    image = read_image(path)

    assert image is not None
    assert tuple(image[0, 0]) == (0, 0, 255)


def test_read_image_returns_none_when_unreadable(tmp_path):
    (tmp_path / "notes.png").write_text("not an image")

    assert read_image(tmp_path / "notes.png") is None
    assert read_image(tmp_path / "missing.png") is None
