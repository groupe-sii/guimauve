import pytest

from guimauve.enums import Button, MouseDirection
from guimauve.models.element import Element


def at(x, y, **kwargs) -> Element:
    return Element(name="target", x=x, y=y, **kwargs)


def moves(inputs) -> list[tuple[int, int]]:
    return [(call[1], call[2]) for call in inputs() if call[0] == "mouse_move"]


def test_move_without_element_does_nothing(controller, inputs):
    controller.move()
    assert inputs() == []


def test_move_without_speed_jumps_to_target(controller, inputs):
    controller.move(on=at(100, 50))
    assert inputs() == [("mouse_move", 100, 50)]


def test_move_to_relative_coordinates(controller, fake_driver, inputs):
    fake_driver.position = (50, 50)
    controller.move(on=Element(name="target", rel_x=10, rel_y=-5))
    assert inputs() == [("mouse_move", 60, 45)]


def test_move_with_speed_interpolates_from_current_position(controller, inputs):
    controller.move(on=at(100, 0, mouse_speed=100))
    path = moves(inputs)
    assert path[0] == (0, 0)
    assert path[-1] == (100, 0)
    assert all(y == 0 for _, y in path)
    assert [x for x, _ in path] == sorted(x for x, _ in path)


def test_move_with_speed_lasts_distance_over_speed(controller, sleeps):
    controller.move(on=at(100, 0, mouse_speed=100))
    assert sum(sleeps) == pytest.approx(1.0, rel=0.02)


def test_move_xy_x_goes_horizontally_first(controller, inputs):
    controller.move(on=at(100, 50, mouse_speed=1000, mouse_direction=MouseDirection.XY_X))
    path = moves(inputs)
    corner = path.index((100, 0))
    assert all(y == 0 for _, y in path[:corner])
    assert all(x == 100 for x, _ in path[corner:])


def test_move_xy_y_goes_vertically_first(controller, inputs):
    controller.move(on=at(100, 50, mouse_speed=1000, mouse_direction=MouseDirection.XY_Y))
    path = moves(inputs)
    corner = path.index((0, 50))
    assert all(x == 0 for x, _ in path[:corner])
    assert all(y == 50 for _, y in path[corner:])


def test_click_moves_then_clicks(controller, inputs):
    controller.click(on=at(10, 20))
    assert inputs() == [("mouse_move", 10, 20), ("mouse_down", Button.LEFT), ("mouse_up", Button.LEFT)]


def test_click_without_element_clicks_in_place(controller, inputs):
    controller.click()
    assert inputs() == [("mouse_down", Button.LEFT), ("mouse_up", Button.LEFT)]


@pytest.mark.parametrize(
    ("action", "button", "count"),
    [
        ("click", Button.LEFT, 1),
        ("double_click", Button.LEFT, 2),
        ("triple_click", Button.LEFT, 3),
        ("right_click", Button.RIGHT, 1),
    ],
)
def test_click_variants(controller, inputs, action, button, count):
    getattr(controller, action)(on=at(10, 20))
    assert inputs() == [("mouse_move", 10, 20)] + [("mouse_down", button), ("mouse_up", button)] * count


def test_click_count(controller, inputs):
    controller.click(count=4)
    assert inputs() == [("mouse_down", Button.LEFT), ("mouse_up", Button.LEFT)] * 4


def test_scroll_in_place(controller, inputs):
    controller.scroll(v=-3, h=1)
    assert inputs() == [("mouse_scroll", -3, 1)]


def test_scroll_moves_first(controller, inputs):
    controller.scroll(v=-3, on=at(10, 20))
    assert inputs() == [("mouse_move", 10, 20), ("mouse_scroll", -3, 0)]


def test_drag_presses_moves_and_releases(controller, inputs):
    controller.drag(on=at(10, 20), button=Button.RIGHT)
    assert inputs() == [("mouse_down", Button.RIGHT), ("mouse_move", 10, 20), ("mouse_up", Button.RIGHT)]


def test_sleep_argument_overrides_default_sleep(make_controller, sleeps):
    make_controller(parameters={"sleep": 0.2}).click(sleep=0.5)
    assert sleeps[-1] == 0.5


@pytest.mark.parametrize("action", ["click", "double_click", "triple_click", "right_click", "scroll", "drag"])
def test_action_on_element_pauses_after_move_then_sleeps(make_controller, sleeps, action):
    getattr(make_controller(parameters={"sleep": 0.2}), action)(on=at(10, 20))
    assert sleeps == [0.2, 0.2]


def test_sleep_argument_does_not_change_pause_after_move(make_controller, sleeps):
    make_controller(parameters={"sleep": 0.2}).click(on=at(10, 20), sleep=0.5)
    assert sleeps == [0.2, 0.5]
