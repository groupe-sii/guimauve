import enum
import json

import pytest
import yaml

from guimauve.models.model import Model


class Color(enum.Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


class Doc(Model):
    title: str = "café"
    count: int = 3
    color: Color = Color.RED


class Outer(Model):
    label: str = "top"
    inner: Doc = Doc()


DATA = {"title": "café", "count": 3, "color": "RED"}


# --- from_dict ---


def test_from_dict_builds_instance():
    m = Doc.from_dict({"title": "hi", "count": 7, "color": "BLUE"})
    assert m.title == "hi"
    assert m.count == 7


def test_from_dict_is_deferred():
    m = Doc.from_dict({"count": "oops"})  # invalid, must not raise
    assert m.count == "oops"
    assert len(m.resolve()) == 1


# --- from_json ---


def test_from_json_from_str():
    m = Doc.from_json(json.dumps(DATA))
    assert m.to_dict(json_mode=True) == DATA


def test_from_json_from_bytes():
    m = Doc.from_json(json.dumps(DATA).encode())
    assert m.to_dict(json_mode=True) == DATA


# --- from_file ---


def test_from_file_json(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(DATA))
    m = Doc.from_file(p)
    assert m.to_dict(json_mode=True) == DATA


def test_from_file_yaml(tmp_path):
    p = tmp_path / "doc.yaml"
    p.write_text(yaml.safe_dump(DATA, allow_unicode=True))
    m = Doc.from_file(p)
    assert m.to_dict(json_mode=True) == DATA


def test_from_file_yml(tmp_path):
    p = tmp_path / "doc.yml"
    p.write_text(yaml.safe_dump(DATA, allow_unicode=True))
    m = Doc.from_file(p)
    assert m.to_dict(json_mode=True) == DATA


def test_from_file_unsupported_extension_raises(tmp_path):
    p = tmp_path / "doc.txt"
    p.write_text("whatever")
    with pytest.raises(ValueError):
        Doc.from_file(p)


# --- round trips ---


def test_round_trip_json_preserves_serialized_form():
    orig = Doc()
    loaded = Doc.from_json(orig.to_json())
    assert loaded.to_dict(json_mode=True) == orig.to_dict(json_mode=True)


def test_round_trip_with_resolve_restores_types_and_equality():
    orig = Doc()
    loaded = Doc.from_json(orig.to_json())
    # before resolve, the enum came back as its name (string)
    assert loaded.color == "RED"
    assert loaded != orig
    # resolve restores the enum member and full equality
    assert loaded.resolve() == []
    assert loaded.color is Color.RED
    assert loaded == orig


def test_round_trip_via_file(tmp_path):
    orig = Doc(title="hé", count=42, color=Color.GREEN)
    p = tmp_path / "doc.yaml"
    orig.to_file(p)
    loaded = Doc.from_file(p)
    assert loaded.resolve() == []
    assert loaded == orig


# --- nested models: load + round trip ---


def test_from_dict_nested_is_deferred_dict():
    # load does not descend either: nested stays a dict until resolve
    o = Outer.from_dict({"inner": {"title": "hi", "count": 2, "color": "RED"}})
    assert isinstance(o.inner, dict)


def test_round_trip_nested_with_resolve():
    orig = Outer(inner=Doc(title="hé", count=7, color=Color.GREEN))
    loaded = Outer.from_json(orig.to_json())
    assert loaded.resolve() == []
    assert isinstance(loaded.inner, Doc)
    assert loaded == orig


def test_round_trip_nested_via_file(tmp_path):
    orig = Outer(inner=Doc(count=3, color=Color.BLUE))
    p = tmp_path / "outer.yaml"
    orig.to_file(p)
    loaded = Outer.from_file(p)
    assert loaded.resolve() == []
    assert loaded == orig
