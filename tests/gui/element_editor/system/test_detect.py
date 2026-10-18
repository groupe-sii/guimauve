import pytest

from guimauve.gui.element_editor_next.system import Platform, current_platform
from guimauve.gui.element_editor_next.system.detect import detect


@pytest.mark.parametrize(
    ("qt_platform", "expected"),
    [
        ("windows", Platform.WINDOWS),
        ("xcb", Platform.X11),
        ("wayland", Platform.WAYLAND),
        ("wayland-egl", Platform.WAYLAND),
        ("offscreen", Platform.OTHER),
        ("cocoa", Platform.OTHER),
    ],
)
def test_detect(qt_platform, expected):
    assert detect(qt_platform) is expected


def test_offscreen_has_no_native_window(qapp):
    assert current_platform() is Platform.OTHER
