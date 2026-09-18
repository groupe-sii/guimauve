import threading
import time

import pytest

from guimauve.enums import Button, Key
from guimauve.models.input_event import InputEvent
from guimauve.recorder.recorder import Recorder

# --- Fake pynput inputs --------------------------------------------------


class FakePynputKey:
    """Placeholder passed to _on_press / _on_release.
    Ignored by monkeypatched key_from_pynput, so needs no real behavior."""


class FakePynputButton:
    """Placeholder passed to _on_click."""


# --- Fixtures ------------------------------------------------------------


@pytest.fixture
def fake_time(monkeypatch):
    counter = {"value": 0.0}

    def fake_perf_counter():
        counter["value"] += 0.1
        return counter["value"]

    # Patch the reference Pydantic captured at class creation
    field = InputEvent.model_fields["t"]
    monkeypatch.setattr(field, "default_factory", fake_perf_counter)
    return counter


@pytest.fixture
def recorder(monkeypatch, fake_listener_cls):
    """Recorder built with fake listeners so no real pynput code runs."""
    monkeypatch.setattr("guimauve.recorder.recorder.keyboard.Listener", fake_listener_cls)
    monkeypatch.setattr("guimauve.recorder.recorder.mouse.Listener", fake_listener_cls)
    return Recorder()


# --- Tests: _record ------------------------------------------------------


def test_record_appends_input_event(recorder, fake_time):
    recorder._record("mouse_move", [10, 20])

    assert len(recorder._events) == 1
    event = recorder._events[0]
    assert isinstance(event, InputEvent)
    assert event.action == "mouse_move"
    assert event.args == [10, 20]
    assert event.t == pytest.approx(0.1)


def test_record_multiple_events_get_increasing_timestamps(recorder, fake_time):
    recorder._record("mouse_move", [1, 1])
    recorder._record("mouse_move", [2, 2])
    recorder._record("mouse_move", [3, 3])

    ts = [e.t for e in recorder._events]
    assert ts == pytest.approx([0.1, 0.2, 0.3])


# --- Tests: _on_move / _on_scroll ---------------------------------------


def test_on_move_records_coordinates(recorder, fake_time):
    recorder._on_move(100, 200)

    assert recorder._events[0].action == "mouse_move"
    assert recorder._events[0].args == [100, 200]


def test_on_scroll_records_deltas(recorder, fake_time):
    recorder._on_scroll(0, 0, 1, -2)

    assert recorder._events[0].action == "mouse_scroll"
    assert recorder._events[0].args == [1, -2]


# --- Tests: _on_press ----------------------------------------------------


def test_on_press_records_key_down_with_enum(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.key_from_pynput",
        lambda k: Key.A,
    )
    recorder._on_press(FakePynputKey())

    assert recorder._events[0].action == "key_down"
    assert recorder._events[0].args == [Key.A]


def test_on_press_unknown_key_records_nothing(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.key_from_pynput",
        lambda k: None,
    )
    recorder._on_press(FakePynputKey())

    assert recorder._events == []


def test_on_press_stop_key_sets_signal_and_records_nothing(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.key_from_pynput",
        lambda k: Key.ESC,
    )
    recorder._stop_key = Key.ESC

    recorder._on_press(FakePynputKey())

    assert recorder._events == []
    assert recorder._stop_signal.is_set()


def test_on_press_unknown_key_does_not_trigger_stop(recorder, fake_time, monkeypatch):
    """Both stop_key and the pressed key resolve to None: the key must
    still be discarded, not mistaken for the stop key."""
    monkeypatch.setattr(
        "guimauve.recorder.recorder.key_from_pynput",
        lambda k: None,
    )
    assert recorder._stop_key is None

    recorder._on_press(FakePynputKey())

    assert recorder._events == []
    assert not recorder._stop_signal.is_set()


# --- Tests: _on_release --------------------------------------------------


def test_on_release_records_key_up_with_enum(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.key_from_pynput",
        lambda k: Key.A,
    )
    recorder._on_release(FakePynputKey())

    assert recorder._events[0].action == "key_up"
    assert recorder._events[0].args == [Key.A]


def test_on_release_unknown_key_records_nothing(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.key_from_pynput",
        lambda k: None,
    )
    recorder._on_release(FakePynputKey())

    assert recorder._events == []


# --- Tests: _on_click ----------------------------------------------------


def test_on_click_press_records_mouse_down_with_enum(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.button_from_pynput",
        lambda b: Button.LEFT,
    )
    recorder._on_click(0, 0, FakePynputButton(), pressed=True)

    assert recorder._events[0].action == "mouse_down"
    assert recorder._events[0].args == [Button.LEFT]


def test_on_click_release_records_mouse_up_with_enum(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.button_from_pynput",
        lambda b: Button.LEFT,
    )
    recorder._on_click(0, 0, FakePynputButton(), pressed=False)

    assert recorder._events[0].action == "mouse_up"
    assert recorder._events[0].args == [Button.LEFT]


def test_on_click_unknown_button_records_nothing(recorder, fake_time, monkeypatch):
    monkeypatch.setattr(
        "guimauve.recorder.recorder.button_from_pynput",
        lambda b: None,
    )
    recorder._on_click(0, 0, FakePynputButton(), pressed=True)

    assert recorder._events == []


# --- Tests: start / stop ------------------------------------------------


def test_start_resets_events_and_starts_listeners(recorder, fake_time):
    recorder._events.append("garbage")  # simulate a previous session
    recorder._stop_signal.set()

    recorder.start()

    assert recorder._events == []
    assert not recorder._stop_signal.is_set()
    assert recorder._keyboard.started
    assert recorder._mouse.started


def test_stop_stops_listeners(recorder):
    recorder.stop()

    assert recorder._keyboard.stopped
    assert recorder._mouse.stopped


# --- Tests: wait --------------------------------------------------------


def test_wait_sets_stop_key_and_returns_when_signal_is_set(recorder):
    def release():
        time.sleep(0.05)
        recorder._stop_signal.set()

    threading.Thread(target=release).start()

    recorder.wait(Key.ESC)

    assert recorder._stop_key is Key.ESC
    assert recorder._keyboard.stopped
    assert recorder._mouse.stopped


# --- Tests: events property ---------------------------------------------


def test_events_returns_captured_events(recorder, fake_time):
    recorder._record("mouse_move", [1, 2])
    recorder._record("key_down", [Key.A])

    events = recorder.events
    assert [e.action for e in events] == ["mouse_move", "key_down"]
    assert events[0].args == [1, 2]
    assert events[1].args == [Key.A]


def test_events_returns_a_copy(recorder, fake_time):
    recorder._record("mouse_move", [1, 2])

    events = recorder.events
    events.clear()  # mutating the returned list must not affect the recorder

    assert len(recorder._events) == 1


def test_events_empty_when_nothing_recorded(recorder):
    assert recorder.events == []
