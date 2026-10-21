import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from guimauve.gui.element_editor_next.theme.icons import ICONS_DIR, Icon, icon, icon_file, logo

RED, GREY = "#FF0000", "#808080"


@pytest.mark.parametrize("name", list(Icon))
def test_every_icon_has_its_file(name):
    assert (ICONS_DIR / f"{name}.svg").is_file()


def center(pixmap):
    image = pixmap.toImage()
    return image.pixelColor(image.width() // 2, image.height() // 2).name()


def test_icon_is_drawn_in_its_color(qapp):
    assert center(icon(Icon.X, RED, GREY).pixmap(QSize(24, 24))) == RED.lower()


def test_disabled_icon_is_drawn_in_the_disabled_color(qapp):
    pixmap = icon(Icon.X, RED, GREY).pixmap(QSize(24, 24), QIcon.Mode.Disabled)
    assert center(pixmap) == GREY.lower()


def test_icon_is_rendered_at_the_device_pixel_ratio(qapp):
    pixmap = icon(Icon.X, RED, GREY).pixmap(QSize(24, 24), 2.0)
    assert (pixmap.width(), pixmap.devicePixelRatio()) == (48, 2.0)


def test_icon_file_is_recolored_for_the_stylesheet():
    path = icon_file(Icon.CHEVRON_DOWN, RED)
    assert path.is_file()
    assert RED in path.read_text(encoding="utf-8")
    assert "currentColor" not in path.read_text(encoding="utf-8")


def test_logo_renders(qapp):
    image = logo().pixmap(QSize(24, 24)).toImage()

    assert not image.isNull()
    assert image.pixelColor(12, 12).alpha() == 255  # the overlap, in the middle
