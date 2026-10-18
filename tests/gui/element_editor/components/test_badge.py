import pytest

from guimauve.gui.element_editor_next.components import Badge, Count, CountBadge, Dot, IconLabel
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
