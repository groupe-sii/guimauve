import time

import pytest

from guimauve.enums import Button, Key
from guimauve.models.input_event import InputEvent
from guimauve.recorder.player import Player


@pytest.fixture
def no_sleep(monkeypatch):
    """Neutralize time.sleep so tests run instantly."""
    monkeypatch.setattr(time, "sleep", lambda _: None)


# --- Tests: start dispatches events --------------------------------------


def test_start_dispatches_all_events(fake_driver, no_sleep):
    events = [
        InputEvent(t=0.0, action="key_down", args=[Key.A]),
        InputEvent(t=0.1, action="key_up", args=[Key.A]),
        InputEvent(t=0.2, action="mouse_move", args=[100, 200]),
        InputEvent(t=0.3, action="mouse_down", args=[Button.LEFT]),
        InputEvent(t=0.4, action="mouse_up", args=[Button.LEFT]),
        InputEvent(t=0.5, action="mouse_scroll", args=[0, 1]),
    ]
    player = Player(fake_driver)
    player.start(events)

    assert fake_driver.calls == [
        ("key_down", Key.A),
        ("key_up", Key.A),
        ("mouse_move", 100, 200),
        ("mouse_down", Button.LEFT),
        ("mouse_up", Button.LEFT),
        ("mouse_scroll", 0, 1),
    ]


# --- Tests: start respects timing ----------------------------------------


def test_start_respects_deltas_between_events(fake_driver, monkeypatch):
    events = [
        InputEvent(t=10.0, action="key_down", args=[Key.A]),
        InputEvent(t=10.5, action="key_up", args=[Key.A]),
        InputEvent(t=10.7, action="mouse_move", args=[1, 2]),
    ]
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda d: sleeps.append(d))

    player = Player(fake_driver)
    player.start(events)

    # First event: delta = 0 -> no sleep. Then 0.5, then 0.2.
    assert sleeps == pytest.approx([0.5, 0.2])


# --- Tests: start with empty input ---------------------------------------


def test_start_empty_list_does_nothing(fake_driver, no_sleep):
    player = Player(fake_driver)
    player.start([])

    assert fake_driver.calls == []
