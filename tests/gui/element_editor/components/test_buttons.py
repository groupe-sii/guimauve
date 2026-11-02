import shiboken6
from PySide6.QtCore import QSize

from guimauve.gui.element_editor.components import Button, IconButton, Variant, text_icon_button, with_shortcut
from guimauve.gui.element_editor.theme import DARK, LIGHT, METRICS, Icon, ThemeChoice


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


def test_a_deleted_text_icon_button_lets_the_theme_change(qtbot, theme):
    button = text_icon_button("Draw on screen", Icon.SQUARE_DASHED, theme)
    button.deleteLater()
    qtbot.waitUntil(lambda: not shiboken6.isValid(button))

    theme.set_choice(ThemeChoice.DARK)  # repainting the deleted button would raise


def test_the_icon_of_a_text_button_keeps_a_gap_before_the_text(qtbot, theme):
    button = text_icon_button("Full screen", Icon.SCAN, theme)
    qtbot.addWidget(button)

    assert button.iconSize() == QSize(METRICS.icon + METRICS.icon_text_gap, METRICS.icon)
    assert button.icon().actualSize(button.iconSize()) == button.iconSize()  # the margin is part of the icon
