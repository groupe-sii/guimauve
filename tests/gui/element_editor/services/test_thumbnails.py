import numpy as np
import pytest
from PySide6.QtCore import QSize

from guimauve.gui.element_editor_next.services import ThumbnailCache, crop, fit, thumbnail
from guimauve.models.area import Area
from guimauve.models.variant import ImageVariant

BOX = QSize(56, 32)


@pytest.mark.parametrize(
    ("size", "expected"),
    [((560, 80), (56, 8)), ((100, 200), (16, 32)), ((10, 8), (20, 16)), ((1000, 1), (56, 1))],
)
def test_fit_keeps_the_proportions_and_enlarges_twice_at_most(size, expected):
    assert fit(*size, BOX) == QSize(*expected)


def test_crop_to_the_match_area():
    image = np.arange(20 * 10).reshape(10, 20).astype(np.uint8)

    part = crop(image, Area(left=2, top=1, right=6, bottom=4))

    assert part.shape == (3, 4)
    assert part[0, 0] == image[1, 2]


def test_crop_clips_the_area_to_the_image():
    image = np.zeros((10, 20), np.uint8)

    assert crop(image, Area(left=15, top=5, right=40, bottom=30)).shape == (5, 5)
    assert crop(image, Area(left=30, top=0, right=40, bottom=5)).shape == (10, 20)  # outside: whole image


def test_thumbnail_at_the_pixel_ratio(qapp):
    image = np.zeros((80, 320, 3), np.uint8)

    result = thumbnail(image, None, BOX, ratio=2.0)

    assert (result.width(), result.height()) == (112, 28)
    assert result.devicePixelRatio() == 2.0


def test_thumbnail_shows_the_match_area(qapp):
    image = np.zeros((40, 40, 3), np.uint8)
    image[10:20, 10:30] = (255, 0, 0)

    result = thumbnail(image, Area(left=10, top=10, right=30, bottom=20), BOX)

    assert (result.width(), result.height()) == (40, 20)
    assert result.pixelColor(20, 10).red() == 255


@pytest.fixture
def variant():
    return ImageVariant(name="light", image=np.zeros((40, 120, 3), np.uint8))


def test_cache_computes_once(qapp, variant):
    cache = ThumbnailCache(BOX)

    assert cache.get(1, variant) is cache.get(1, variant)


def test_cache_follows_the_image_and_the_match_area(qapp, variant):
    cache = ThumbnailCache(BOX)
    first = cache.get(1, variant)

    variant.match_area = Area(left=0, top=0, right=40, bottom=40)
    by_area = cache.get(1, variant)
    variant.image = np.zeros((40, 120, 3), np.uint8)
    by_image = cache.get(1, variant)

    assert first is not by_area and by_area is not by_image
    assert (by_area.width(), by_area.height()) == (32, 32)


def test_cache_without_image(qapp):
    assert ThumbnailCache(BOX).get(1, ImageVariant(name="empty")) is None


def test_cache_forgets_removed_variants(qapp, variant):
    cache = ThumbnailCache(BOX)
    first = cache.get(1, variant)

    cache.keep(set())

    assert cache.get(1, variant) is not first
