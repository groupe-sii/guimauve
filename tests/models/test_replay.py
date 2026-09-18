import json

from guimauve.enums import Button, Key
from guimauve.models.input_event import InputEvent
from guimauve.models.replay import Replay


def write_events(tmp_path, events):
    """Write an events list to a temp JSON file and return the path."""
    path = tmp_path / "events.json"
    with path.open("w") as f:
        json.dump(events, f)
    return path


# --- name: not blank ---


def test_name_blank_is_rejected(real_file):
    errors = Replay(name="   ", path=real_file).resolve()
    assert any(e["type"] == "empty" and e["loc"] == ("name",) for e in errors)


# --- source: path or events required ---


def test_no_path_and_no_events_reports_no_source():
    errors = Replay(name="x").resolve()
    assert any(e["type"] == "no_source" for e in errors)


def test_events_only_is_valid():
    r = Replay(name="x", events=[InputEvent(t=0.0, action="key_down", args=[Key.A])])
    assert r.resolve() == []


def test_path_only_is_valid(real_file):
    assert Replay(name="run1", path=real_file).resolve() == []


# --- path: must exist when provided ---


def test_path_not_found_reports_error(tmp_path):
    missing = tmp_path / "nope.json"
    errors = Replay(name="x", path=missing).resolve()
    assert errors[0]["type"] == "file_not_found"
    assert errors[0]["loc"] == ("path",)
    assert errors[0]["ctx"]["path"] == str(missing)


# --- load(): explicit, idempotent, coerces enums, excluded from dump ---


def test_load_populates_events_and_returns_self(tmp_path):
    path = write_events(
        tmp_path,
        [
            {"t": 0.0, "action": "key_down", "args": ["A"]},
            {"t": 0.1, "action": "key_up", "args": ["A"]},
        ],
    )
    r = Replay(name="x", path=path)
    result = r.load()

    assert result is r  # returns self for chaining
    assert len(r.events) == 2
    assert r.events[0].action == "key_down"


def test_load_coerces_key_strings_to_enum(tmp_path):
    path = write_events(tmp_path, [{"t": 0.0, "action": "key_down", "args": ["A"]}])
    r = Replay(name="x", path=path).load()

    assert r.events[0].args == [Key.A]


def test_load_coerces_button_strings_to_enum(tmp_path):
    path = write_events(tmp_path, [{"t": 0.0, "action": "mouse_down", "args": ["LEFT"]}])
    r = Replay(name="x", path=path).load()

    assert r.events[0].args == [Button.LEFT]


def test_load_keeps_move_and_scroll_args_unchanged(tmp_path):
    path = write_events(
        tmp_path,
        [
            {"t": 0.0, "action": "mouse_move", "args": [100, 200]},
            {"t": 0.1, "action": "mouse_scroll", "args": [0, 1]},
        ],
    )
    r = Replay(name="x", path=path).load()

    assert r.events[0].args == [100, 200]
    assert r.events[1].args == [0, 1]


def test_load_is_idempotent(tmp_path):
    path = write_events(tmp_path, [{"t": 0.0, "action": "key_down", "args": ["A"]}])
    r = Replay(name="x", path=path).load()
    first = r.events
    r.load()

    assert r.events is first  # not reloaded


def test_load_empty_file(tmp_path):
    path = write_events(tmp_path, [])
    r = Replay(name="x", path=path).load()

    assert r.events == []


def test_events_excluded_from_dump(tmp_path):
    path = write_events(tmp_path, [{"t": 0.0, "action": "key_down", "args": ["A"]}])
    r = Replay(name="x", path=path).load()

    assert "events" not in r.to_dict()
    assert "events" not in r.to_dict(json_mode=True)


# --- private attrs / properties ---


def test_alias_is_new_and_resolved_defaults(real_file):
    r = Replay(name="x", path=real_file)
    assert r.alias is None
    assert r.is_new is False
    assert r.resolved is False
