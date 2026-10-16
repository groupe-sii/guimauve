from PySide6.QtCore import QSize

from guimauve.gui.element_editor_next.components import Button, IconButton, Variant, with_shortcut
from guimauve.gui.element_editor_next.theme import DARK, LIGHT, Icon, ThemeChoice


def test_button_carries_its_variant(qtbot):
    button = Button("Save", Variant.PRIMARY)
    qtbot.addWidget(button)
    assert button.property("variant") == "primary"


def test_tooltip_shows_the_shortcut():
    assert with_shortcut("Duplicate", "Ctrl+D") == "Duplicate (Ctrl+D)"
    assert with_shortcut("Duplicate", None) == "Duplicate"


def test_icon_button_follows_the_theme(qtbot, theme):
    button = IconButton(Icon.X, theme, "Remove", role="accent")
    qtbot.addWidget(button)

    def center() -> str:
        return button.icon().pixmap(QSize(24, 24)).toImage().pixelColor(12, 12).name().upper()

    assert center() == LIGHT.accent
    theme.set_choice(ThemeChoice.DARK)
    assert center() == DARK.accent
