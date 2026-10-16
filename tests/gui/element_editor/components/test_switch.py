import pytest
from PySide6.QtCore import Qt

from guimauve.gui.element_editor_next.components import Switch
from guimauve.gui.element_editor_next.theme import DARK, LIGHT, ThemeChoice


@pytest.fixture
def switch(qtbot, theme):
    switch = Switch(theme)
    qtbot.addWidget(switch)
    switch.resize(switch.sizeHint())
    return switch


def track_left(switch) -> tuple[int, int]:
    """A point of the track that the knob never covers when the switch is on."""
    return 6, switch.height() // 2


def test_click_toggles(qtbot, switch):
    with qtbot.waitSignal(switch.clicked):
        qtbot.mouseClick(switch, Qt.MouseButton.LeftButton)
    assert switch.isChecked()


def test_space_toggles(qtbot, switch):
    qtbot.keyClick(switch, Qt.Key.Key_Space)
    assert switch.isChecked()


def test_colors_follow_the_state_and_the_theme(switch, theme, color_at):
    switch.setChecked(True)
    assert color_at(switch, *track_left(switch)) == LIGHT.accent_fill
    theme.set_choice(ThemeChoice.DARK)
    assert color_at(switch, *track_left(switch)) == DARK.accent_fill


def test_off_uses_the_switch_track(switch, color_at):
    x, y = track_left(switch)
    assert color_at(switch, switch.width() - x, y) == LIGHT.switch_track
