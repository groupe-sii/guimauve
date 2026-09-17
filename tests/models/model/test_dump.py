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
    title: str = "café"  # unicode + declared first (not alphabetical)
    count: int = 3
    color: Color = Color.RED


class Outer(Model):
    label: str = "top"
    inner: Doc = Doc()


EXPECTED_JSON = {"title": "café", "count": 3, "color": "RED"}


# --- to_dict ---


def test_to_dict_python_mode_keeps_enum_object():
    assert Doc().to_dict() == {"title": "café", "count": 3, "color": Color.RED}


def test_to_dict_json_mode_serializes_enum_name():
    assert Doc().to_dict(json_mode=True) == EXPECTED_JSON


def test_to_dict_dumps_raw_state_without_validating():
    m = Doc(count="oops")  # invalid, deferred -> no raise
    with pytest.warns(UserWarning):
        assert m.to_dict()["count"] == "oops"


# --- to_json ---


def test_to_json_round_trips_to_expected_dict():
    assert json.loads(Doc().to_json()) == EXPECTED_JSON


def test_to_json_without_indent_is_compact():
    assert "\n" not in Doc().to_json()


def test_to_json_with_indent_is_pretty():
    s = Doc().to_json(indent=2)
    assert "\n" in s
    assert json.loads(s) == EXPECTED_JSON


# --- to_yaml ---


def test_to_yaml_round_trips_to_expected_dict():
    assert yaml.safe_load(Doc().to_yaml()) == EXPECTED_JSON


def test_to_yaml_preserves_field_order():
    loaded = yaml.safe_load(Doc().to_yaml())
    assert list(loaded.keys()) == ["title", "count", "color"]


def test_to_yaml_keeps_unicode_literal():
    assert "café" in Doc().to_yaml()


# --- to_file ---


def test_to_file_json(tmp_path):
    p = tmp_path / "doc.json"
    Doc().to_file(p)
    text = p.read_text()
    assert json.loads(text) == EXPECTED_JSON
    assert "\n" in text  # written with indent=2


def test_to_file_yaml(tmp_path):
    p = tmp_path / "doc.yaml"
    Doc().to_file(p)
    assert yaml.safe_load(p.read_text()) == EXPECTED_JSON


def test_to_file_yml(tmp_path):
    p = tmp_path / "doc.yml"
    Doc().to_file(p)
    assert yaml.safe_load(p.read_text()) == EXPECTED_JSON


def test_to_file_unsupported_extension_raises(tmp_path):
    p = tmp_path / "doc.txt"
    with pytest.raises(ValueError):
        Doc().to_file(p)


# --- nested models: dump is recursive ---


def test_to_dict_json_mode_is_recursive():
    o = Outer(inner=Doc(title="hi", count=1, color=Color.BLUE))
    assert o.to_dict(json_mode=True) == {
        "label": "top",
        "inner": {"title": "hi", "count": 1, "color": "BLUE"},
    }


def test_to_dict_python_mode_keeps_nested_enum_object():
    o = Outer(inner=Doc(color=Color.RED))
    assert o.to_dict()["inner"]["color"] is Color.RED


def test_to_yaml_is_recursive_and_preserves_nested_order():
    o = Outer(inner=Doc())
    loaded = yaml.safe_load(o.to_yaml())
    assert list(loaded["inner"].keys()) == ["title", "count", "color"]
