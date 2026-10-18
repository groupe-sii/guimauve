from guimauve.gui.element_editor_next.components import IconLabel
from guimauve.gui.element_editor_next.theme import DARK, LIGHT, Icon, ThemeChoice


def center(label) -> str:
    image = label.pixmap().toImage()
    return image.pixelColor(image.width() // 2, image.height() // 2).name().upper()


def test_icon_follows_the_theme(qtbot, theme):
    label = IconLabel(Icon.X, theme, "error")
    qtbot.addWidget(label)
    assert center(label) == LIGHT.error
    theme.set_choice(ThemeChoice.DARK)
    assert center(label) == DARK.error


def test_icon_can_change(qtbot, theme):
    label = IconLabel(Icon.X, theme, "error")
    qtbot.addWidget(label)
    label.set_icon(Icon.X, "accent")
    assert center(label) == LIGHT.accent
