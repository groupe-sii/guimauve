import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton

from guimauve.gui.element_editor_next.components import Banner, IconLabel, Tone
from guimauve.gui.element_editor_next.theme import LIGHT


@pytest.fixture
def make_banner(qtbot, theme):
    def make(tone: Tone = Tone.WARNING, **options) -> Banner:
        banner = Banner('Fixed position: <a href="fixed_position">detection is skipped</a>', tone, theme, **options)
        qtbot.addWidget(banner)
        banner.show()
        return banner

    return make


def test_tone_and_shape_are_read_by_the_stylesheet(make_banner):
    banner = make_banner(Tone.ERROR, strip=True)
    assert (banner.property("banner"), banner.property("strip")) == ("error", True)


@pytest.mark.parametrize(("tone", "role"), [(Tone.ERROR, "error"), (Tone.WARNING, "warning")])
def test_icon_takes_the_color_of_the_tone(make_banner, tone, role):
    banner = make_banner(tone)
    image = banner.findChild(IconLabel).pixmap().toImage()
    pixels = (image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height()))
    assert {pixel.name().upper() for pixel in pixels if pixel.alpha() == 255} == {getattr(LIGHT, role)}


def test_link_gives_its_href(qtbot, make_banner):
    banner = make_banner()
    with qtbot.waitSignal(banner.link_activated) as signal:
        banner.findChild(QLabel, "text").linkActivated.emit("fixed_position")
    assert signal.args == ["fixed_position"]


def test_close_hides_and_emits(qtbot, make_banner):
    banner = make_banner(closable=True)
    with qtbot.waitSignal(banner.closed):
        qtbot.mouseClick(banner.findChild(QToolButton, "close"), Qt.MouseButton.LeftButton)
    assert banner.isHidden()


def test_not_closable_by_default(make_banner):
    assert make_banner().findChild(QToolButton, "close") is None


def test_actions_go_before_the_close_button(qtbot, make_banner):
    banner = make_banner(closable=True)
    action = QPushButton("Show screen at failure")
    banner.add_action(action)
    banner.resize(600, 60)
    qtbot.waitUntil(lambda: action.x() > 0)
    assert action.x() < banner.findChild(QToolButton, "close").x()
