import pytest
from PySide6.QtCore import QPointF, QRectF

from guimauve.gui.element_editor_next.overlays import fit_capture, pixel_at, pixel_rect

SCREEN = QRectF(0, 0, 1000, 500)


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((2000, 500), QRectF(0, 125, 1000, 250)),  # half size, centred
        ((400, 200), QRectF(300, 150, 400, 200)),  # never enlarged
    ],
)
def test_fit_capture(size, expected):
    assert fit_capture(*size, SCREEN) == expected


def test_pixel_at_on_a_scaled_capture():
    shown = QRectF(0, 125, 1000, 250)  # 2000 × 500 at half size

    assert pixel_at(QPointF(10.2, 125.9), shown, 2000, 500) == (20, 1)
    assert pixel_at(QPointF(-50, 900), shown, 2000, 500) == (0, 499)  # kept inside


def test_pixel_rect():
    shown = QRectF(0, 125, 1000, 250)

    assert pixel_rect(20, 2, 40, 6, shown, 2000, 500) == QRectF(10, 126, 10, 2)
