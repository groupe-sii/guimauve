import json
import time
from pathlib import Path

import pytest

from guimauve.enums import Button, Key
from guimauve.models.input_event import InputEvent
from guimauve.recorder.player import Player

# --- Helpers -------------------------------------------------------------


def write_json(tmp_path: Path, events: list) -> Path:
    """Write an events list to a temp JSON file and return the path."""
    path = tmp_path / "events.json"
    with path.open("w") as f:
        json.dump(events, f)
    return path


@pytest.fixture
def no_sleep(monkeypatch):
    """Neutralize time.sleep so tests run instantly."""
    monkeypatch.setattr(time, "sleep", lambda _: None)


# --- Tests: load ---------------------------------------------------------


def test_load_reads_all_events(fake_driver, tmp_path):
    path = write_json(
        tmp_path,
        [
            {"t": 0.0, "action": "key_down", "args": ["A"]},
            {"t": 0.1, "action": "key_up", "args": ["A"]},
        ],
    )
    player = Player(fake_driver)
    player._load(path)

    assert len(player._events) == 2
    assert player._events[0].t == 0.0
    assert player._events[0].action == "key_down"


def test_load_coerces_key_strings_to_enum(fake_driver, tmp_path):
    path = write_json(
        tmp_path,
        [
            {"t": 0.0, "action": "key_down", "args": ["A"]},
            {"t": 0.1, "action": "key_up", "args": ["A"]},
        ],
    )
    player = Player(fake_driver)
    player._load(path)

    assert player._events[0].args == [Key.A]
    assert player._events[1].args == [Key.A]


def test_load_coerces_button_strings_to_enum(fake_driver, tmp_path):
    path = write_json(
        tmp_path,
        [
            {"t": 0.0, "action": "mouse_down", "args": ["LEFT"]},
            {"t": 0.1, "action": "mouse_up", "args": ["LEFT"]},
        ],
    )
    player = Player(fake_driver)
    player._load(path)

    assert player._events[0].args == [Button.LEFT]
    assert player._events[1].args == [Button.LEFT]


def test_load_keeps_move_and_scroll_args_unchanged(fake_driver, tmp_path):
    path = write_json(
        tmp_path,
        [
            {"t": 0.0, "action": "mouse_move", "args": [100, 200]},
            {"t": 0.1, "action": "mouse_scroll", "args": [0, 1]},
        ],
    )
    player = Player(fake_driver)
    player._load(path)

    assert player._events[0].args == [100, 200]
    assert player._events[1].args == [0, 1]


def test_load_empty_file(fake_driver, tmp_path):
    path = write_json(tmp_path, [])
    player = Player(fake_driver)
    player._load(path)

    assert player._events == []


# --- Tests: start (with a Path) ------------------------------------------


def test_start_from_path_dispatches_all_events(fake_driver, tmp_path, no_sleep):
    path = write_json(
        tmp_path,
        [
            {"t": 0.0, "action": "key_down", "args": ["A"]},
            {"t": 0.1, "action": "key_up", "args": ["A"]},
            {"t": 0.2, "action": "mouse_move", "args": [100, 200]},
            {"t": 0.3, "action": "mouse_down", "args": ["LEFT"]},
            {"t": 0.4, "action": "mouse_up", "args": ["LEFT"]},
            {"t": 0.5, "action": "mouse_scroll", "args": [0, 1]},
        ],
    )
    player = Player(fake_driver)
    player.start(path)

    assert fake_driver.calls == [
        ("key_down", Key.A),
        ("key_up", Key.A),
        ("mouse_move", 100, 200),
        ("mouse_down", Button.LEFT),
        ("mouse_up", Button.LEFT),
        ("mouse_scroll", 0, 1),
    ]


# --- Tests: start (with a list) ------------------------------------------


def test_start_from_list_dispatches_all_events(fake_driver, no_sleep):
    events = [
        InputEvent(t=0.0, action="key_down", args=[Key.A]),
        InputEvent(t=0.1, action="key_up", args=[Key.A]),
    ]
    player = Player(fake_driver)
    player.start(events)

    assert fake_driver.calls == [
        ("key_down", Key.A),
        ("key_up", Key.A),
    ]


# --- Tests: start (timing) -----------------------------------------------


def test_start_respects_deltas_between_events(fake_driver, tmp_path, monkeypatch):
    path = write_json(
        tmp_path,
        [
            {"t": 10.0, "action": "key_down", "args": ["A"]},
            {"t": 10.5, "action": "key_up", "args": ["A"]},
            {"t": 10.7, "action": "mouse_move", "args": [1, 2]},
        ],
    )
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda d: sleeps.append(d))

    player = Player(fake_driver)
    player.start(path)

    # First event: delta = 0 -> no sleep. Then 0.5, then 0.2.
    assert sleeps == pytest.approx([0.5, 0.2])


# --- Tests: start (invalid input) ----------------------------------------


def test_start_raises_on_invalid_type(fake_driver):
    player = Player(fake_driver)

    with pytest.raises(TypeError, match="must be a Path or a list"):
        player.start("not a path or a list")


def test_start_empty_list_does_nothing(fake_driver, no_sleep):
    player = Player(fake_driver)
    player.start([])

    assert fake_driver.calls == []


def test_start_empty_path_does_nothing(fake_driver, tmp_path, no_sleep):
    path = write_json(tmp_path, [])
    player = Player(fake_driver)
    player.start(path)

    assert fake_driver.calls == []
