import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QComboBox, QLineEdit, QMenu, QPushButton, QScrollBar, QSpinBox, QToolButton, QWidget

from guimauve.gui.element_editor_next.theme import DARK, LIGHT, Palette
from guimauve.gui.element_editor_next.theme.color import contrast
from guimauve.gui.element_editor_next.theme.style import primary_hover, primary_pressed, qpalette, stylesheet

PALETTES = pytest.mark.parametrize("palette", [LIGHT, DARK], ids=["light", "dark"])


@PALETTES
def test_every_value_is_resolved(palette: Palette):
    assert "$" not in stylesheet(palette)


@PALETTES
@pytest.mark.qt_log_level_fail("WARNING")
def test_qt_accepts_the_stylesheet(qapp, qtbot, palette: Palette):
    root = QWidget()
    qtbot.addWidget(root)
    for widget in (QLineEdit, QSpinBox, QComboBox, QPushButton, QToolButton, QScrollBar, QMenu):
        widget(root)
    root.setStyleSheet(stylesheet(palette))
    root.show()
    for child in root.findChildren(QWidget):
        child.ensurePolished()


@PALETTES
@pytest.mark.parametrize("state", [primary_hover, primary_pressed])
def test_white_text_is_readable_on_primary_states(palette: Palette, state):
    assert contrast("#FFFFFF", state(palette)) >= 4.5


@PALETTES
def test_palette_follows_the_tokens(palette: Palette):
    result = qpalette(palette)
    assert result.color(QPalette.ColorRole.Window).name().upper() == palette.background
    assert result.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name().upper() == palette.text_muted
