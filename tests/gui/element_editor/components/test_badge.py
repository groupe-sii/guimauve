import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from guimauve.gui.element_editor_next.components import Badge, CenteredLabel, Count, CountBadge, Dot, IconLabel
from guimauve.gui.element_editor_next.theme import DARK, LIGHT, METRICS, ThemeChoice


def test_badge_is_styled_as_inherited(qtbot):
    badge = Badge("2")
    qtbot.addWidget(badge)
    assert badge.property("badge") == "inherit"
    assert badge.height() == METRICS.badge_height


def test_dot_follows_the_theme(qtbot, theme, color_at):
    dot = Dot(theme)
    qtbot.addWidget(dot)
    center = METRICS.dot // 2
    assert color_at(dot, center, center) == LIGHT.inherit
    theme.set_choice(ThemeChoice.DARK)
    assert color_at(dot, center, center) == DARK.inherit


@pytest.mark.parametrize("kind", list(Count))
def test_count_badge_has_an_icon_and_a_count(qtbot, theme, kind):
    badge = CountBadge(kind, theme)
    qtbot.addWidget(badge)
    badge.set_count(3)
    assert badge.property("badge") == kind.value
    assert badge.findChild(IconLabel) is not None
    assert badge.count() == 3
    badge.set_count(0)
    assert badge.isHidden()


def _ink_rows(image, x0: int, x1: int) -> tuple[int, int]:
    """First and last rows holding a dark pixel between two columns, on a white background."""

    def inked(y: int) -> bool:
        return any(image.pixelColor(x, y).lightness() < 180 for x in range(x0, x1))

    rows = [y for y in range(image.height()) if inked(y)]
    return rows[0], rows[-1]


def test_number_is_centered_on_its_icon(theme, qtbot):
    badge = CountBadge(Count.ERROR, theme)
    badge.set_count(8)
    qtbot.addWidget(badge)
    badge.show()
    icon = badge.findChild(IconLabel)
    number = badge.findChild(CenteredLabel)

    image = QImage(badge.size(), QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.white)
    badge.render(image)
    icon_top, icon_bottom = _ink_rows(image, icon.x(), icon.x() + icon.width())
    top, bottom = _ink_rows(image, number.x(), number.x() + number.width())

    assert abs((top + bottom) - (icon_top + icon_bottom)) <= 1  # centers within half a pixel
