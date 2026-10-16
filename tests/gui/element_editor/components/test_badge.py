from guimauve.gui.element_editor_next.components import Badge, Dot
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
