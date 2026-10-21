import pytest


@pytest.fixture
def color_at():
    """Color of the pixel at (x, y) of a rendered widget, as #RRGGBB."""

    def color(widget, x: int, y: int) -> str:
        return widget.grab().toImage().pixelColor(x, y).name().upper()

    return color
