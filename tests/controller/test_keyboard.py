import pytest

from guimauve.enums import Button, Key


def test_type_pastes_whole_text_without_interval(controller, inputs):
    controller.type("hello")
    assert inputs() == [("paste", "hello")]


def test_type_types_char_by_char_with_interval(controller, inputs, sleeps):
    controller.type("abc", interval=0.1)
    assert inputs() == [("type", "a"), ("type", "b"), ("type", "c")]
    assert sleeps.count(0.1) == 3


def test_press_single_key(controller, inputs):
    controller.press(Key.ENTER)
    assert inputs() == [("key_down", Key.ENTER), ("key_up", Key.ENTER)]


def test_press_combination_releases_in_reverse_order(controller, inputs):
    controller.press(Key.CTRL, Key.SHIFT, Key.ESC)
    assert inputs() == [
        ("key_down", Key.CTRL),
        ("key_down", Key.SHIFT),
        ("key_down", Key.ESC),
        ("key_up", Key.ESC),
        ("key_up", Key.SHIFT),
        ("key_up", Key.CTRL),
    ]


def test_press_waits_interval_after_each_key_down(controller, sleeps):
    controller.press(Key.CTRL, Key.ESC, interval=0.1)
    assert sleeps.count(0.1) == 2


def test_down_accepts_keys_and_buttons(controller, inputs):
    controller.down(Key.CTRL, Button.LEFT)
    assert inputs() == [("key_down", Key.CTRL), ("mouse_down", Button.LEFT)]


def test_up_accepts_keys_and_buttons(controller, inputs):
    controller.up(Key.CTRL, Button.LEFT)
    assert inputs() == [("key_up", Key.CTRL), ("mouse_up", Button.LEFT)]


@pytest.mark.parametrize("method", ["down", "up"])
def test_down_up_reject_unsupported_argument(controller, method):
    with pytest.raises(ValueError):
        getattr(controller, method)("a")


def test_hold_releases_on_exit(controller, inputs):
    with controller.hold(Key.SHIFT, Button.LEFT):
        assert inputs() == [("key_down", Key.SHIFT), ("mouse_down", Button.LEFT)]
    assert inputs()[2:] == [("key_up", Key.SHIFT), ("mouse_up", Button.LEFT)]


def test_hold_releases_when_body_raises(controller, inputs):
    with pytest.raises(RuntimeError):
        with controller.hold(Key.SHIFT):
            raise RuntimeError
    assert inputs()[-1] == ("key_up", Key.SHIFT)


def test_hold_does_not_pause(make_controller, sleeps):
    with make_controller(parameters={"sleep": 0.2}).hold(Key.SHIFT):
        pass
    assert sleeps == []


def test_hold_body_actions_are_root_actions(controller):
    with controller.hold(Key.SHIFT):
        assert controller._root_action is None
