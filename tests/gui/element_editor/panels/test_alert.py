import pytest

from guimauve.gui.element_editor_next.panels import AlertBanner, alert_text


@pytest.mark.parametrize(
    ("message", "action", "text"),
    [
        ("Element not found", "click", "Element not found, while running click()"),
        ("Element not found", "manual_call", "Element not found"),
        ("Element not found", "", "Element not found"),
        ("Size <0", "", "Size &lt;0"),
    ],
)
def test_text(message, action, text):
    assert alert_text(message, action) == text


def test_hidden_without_a_message(theme, qtbot):
    banner = AlertBanner("", "", theme)
    qtbot.addWidget(banner)

    assert banner.isHidden()


def test_shown_with_a_message(theme, qtbot):
    banner = AlertBanner("Element not found", "click", theme)
    qtbot.addWidget(banner)
    banner.show()

    assert banner.isVisible()
