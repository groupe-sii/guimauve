import pytest

from guimauve.gui.element_editor_next.canvas.region import Grip, Region, drawn, handle_points, move, resize
from guimauve.models.area import Area

REGION = Region(10, 20, 50, 40)


def test_area_round_trip():
    area = Area(left=1, top=2, right=3, bottom=4)

    assert Region.of(area).area() == area
    assert Region.whole(30, 20) == Region(0, 0, 30, 20)


def test_handles_on_the_edges_and_corners():
    points = handle_points(REGION)

    assert points[Grip.TOP_LEFT] == (10, 20)
    assert points[Grip.BOTTOM] == (30, 40)
    assert points[Grip.RIGHT] == (50, 30)
    assert len(points) == 8


@pytest.mark.parametrize(
    ("grip", "x", "y", "expected"),
    [
        (Grip.TOP_LEFT, 4.4, 15.6, Region(4, 16, 50, 40)),
        (Grip.RIGHT, 70.2, 0, Region(10, 20, 70, 40)),
        (Grip.BOTTOM, 0, 33, Region(10, 20, 50, 33)),
        (Grip.LEFT, -30, 99, Region(0, 20, 50, 40)),  # stops at the image
        (Grip.BOTTOM_RIGHT, 500, 500, Region(10, 20, 100, 60)),
        (Grip.LEFT, 80, 0, Region(49, 20, 50, 40)),  # one pixel left at least
        (Grip.TOP, 0, 45, Region(10, 39, 50, 40)),
    ],
)
def test_resize(grip, x, y, expected):
    assert resize(REGION, grip, x, y, 100, 60) == expected


@pytest.mark.parametrize(
    ("dx", "dy", "expected"),
    [(5, -3, Region(15, 17, 55, 37)), (-50, 0, Region(0, 20, 40, 40)), (0, 99, Region(10, 40, 50, 60))],
)
def test_move_stays_inside(dx, dy, expected):
    assert move(REGION, dx, dy, 100, 60) == expected


def test_drawn_covers_both_pixels_in_any_direction():
    assert drawn((30, 25), (10, 5), 100, 60) == Region(10, 5, 31, 26)
    assert drawn((5, 5), (5, 5), 100, 60) == Region(5, 5, 6, 6)
    assert drawn((-10, 50), (200, 70), 100, 60) == Region(0, 50, 100, 60)
