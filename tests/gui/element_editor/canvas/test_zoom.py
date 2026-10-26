import pytest

from guimauve.gui.element_editor_next.canvas import zoom


@pytest.mark.parametrize(
    ("size", "view", "expected"),
    [
        ((1000, 500), (550, 400), 0.55),  # limited by the width
        ((1000, 500), (800, 200), 0.4),  # limited by the height
        ((100, 50), (600, 400), 2.0),  # a small image is enlarged twice at most
        ((100_000, 10), (100, 100), zoom.MIN_ZOOM),
        ((100, 50), (0, 400), 1.0),  # view not laid out yet
    ],
)
def test_fit(size, view, expected):
    assert zoom.fit(*size, *view) == pytest.approx(expected)


def test_wheel_zooms_by_steps_within_bounds():
    assert zoom.wheel(1.0, 1) == pytest.approx(zoom.WHEEL_STEP)
    assert zoom.wheel(1.0, -2) == pytest.approx(1 / zoom.WHEEL_STEP**2)
    assert zoom.wheel(zoom.MAX_ZOOM, 3) == zoom.MAX_ZOOM
    assert zoom.wheel(zoom.MIN_ZOOM, -3) == zoom.MIN_ZOOM


@pytest.mark.parametrize(("current", "after_in", "after_out"), [(1.0, 1.5, 0.75), (1.2, 1.5, 1.0), (32.0, 32.0, 24.0)])
def test_buttons_go_to_the_next_level(current, after_in, after_out):
    assert zoom.zoom_in(current) == after_in
    assert zoom.zoom_out(current) == after_out


def test_zoom_out_stops_at_the_minimum():
    assert zoom.zoom_out(zoom.MIN_ZOOM) == zoom.MIN_ZOOM


@pytest.mark.parametrize(("value", "text"), [(1.0, "100 %"), (1.914, "191 %"), (0.05, "5 %")])
def test_label(value, text):
    assert zoom.label(value) == text
