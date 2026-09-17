import enum
from typing import Optional

from guimauve.models.model import Model


class Color(enum.Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


class Palette(Model):
    color: Color = Color.RED
    name: str = "x"


class OptionalPalette(Model):
    color: Optional[Color] = None


class Wrapper(Model):
    inner: Palette = Palette()


class Container(Model):
    keys: list[Color] = []
    palette: dict[str, Color] = {}
    maybe: Optional[list[Color]] = None


# --- Key subtlety: coercion happens at validation, not at construction ---


def test_name_stays_string_after_construction():
    m = Palette(color="RED")
    assert m.color == "RED"
    assert not isinstance(m.color, Color)


def test_name_becomes_enum_after_resolve():
    m = Palette(color="RED")
    assert m.resolve() == []
    assert m.color is Color.RED


# --- Coercion by name through the validation path ---


def test_valid_name_coerces():
    m = Palette(color="BLUE")
    assert m.resolve() == []
    assert m.color is Color.BLUE


def test_invalid_name_reports_error():
    m = Palette(color="PURPLE")
    errors = m.resolve()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("color",)


def test_value_is_accepted():
    m = Palette(color=1)  # 1 is Color.RED's value
    assert m.resolve() == []
    assert m.color is Color.RED


def test_enum_member_passed_directly_is_valid():
    m = Palette(color=Color.GREEN)
    assert m.resolve() == []
    assert m.color is Color.GREEN


# --- Optional[Enum] ---


def test_optional_enum_coerces_name():
    m = OptionalPalette(color="RED")
    assert m.resolve() == []
    assert m.color is Color.RED


def test_optional_enum_none_stays_none():
    m = OptionalPalette(color=None)
    assert m.resolve() == []
    assert m.color is None


# --- Serialization: name in JSON mode, enum object in python mode ---


def test_json_mode_serializes_enum_as_name():
    m = Palette(color=Color.RED)
    assert m.to_dict(json_mode=True) == {"color": "RED", "name": "x"}


def test_python_mode_keeps_enum_object():
    m = Palette(color=Color.RED)
    assert m.to_dict() == {"color": Color.RED, "name": "x"}


# --- Round trip: name -> enum -> name ---


def test_round_trip_name_enum_name():
    m = Palette(color="GREEN")
    assert m.resolve() == []
    assert m.color is Color.GREEN
    assert m.to_dict(json_mode=True)["color"] == "GREEN"


# --- nested models: enum coercion descends ---


def test_nested_enum_coerces_on_resolve():
    w = Wrapper(inner={"color": "BLUE"})
    assert w.resolve() == []
    assert w.inner.color is Color.BLUE


def test_nested_invalid_enum_reports_nested_loc():
    w = Wrapper(inner={"color": "PURPLE"})
    errors = w.resolve()
    assert len(errors) == 1
    assert errors[0]["loc"] == ("inner", "color")
    assert errors[0]["type"] == "enum_name"


def test_nested_enum_serializes_as_name_in_json_mode():
    w = Wrapper(inner=Palette(color=Color.GREEN))
    assert w.to_dict(json_mode=True) == {"inner": {"color": "GREEN", "name": "x"}}


# --- enums inside containers: coercion + serialization by name ---


def test_list_coerces_names_and_serializes_by_name():
    kb = Container(keys=["RED", "BLUE"])
    assert kb.resolve() == []
    assert kb.keys == [Color.RED, Color.BLUE]
    assert kb.to_dict(json_mode=True)["keys"] == ["RED", "BLUE"]


def test_dict_values_coerce_names_and_serialize_by_name():
    kb = Container(palette={"a": "GREEN"})
    assert kb.resolve() == []
    assert kb.palette["a"] is Color.GREEN
    assert kb.to_dict(json_mode=True)["palette"] == {"a": "GREEN"}


def test_optional_list_of_enum_coerces():
    kb = Container(maybe=["RED"])
    assert kb.resolve() == []
    assert kb.maybe == [Color.RED]


def test_optional_list_none_stays_none():
    kb = Container(maybe=None)
    assert kb.resolve() == []
    assert kb.maybe is None


def test_invalid_name_in_list_reports_element_loc():
    # inside a container, an invalid name falls through to pydantic
    # -> precise element loc, rather than the field loc
    kb = Container(keys=["RED", "BOGUS"])
    errors = kb.resolve()
    assert any(e["loc"] == ("keys", 1) for e in errors)


def test_container_round_trip():
    kb = Container(keys=[Color.RED, Color.GREEN], palette={"x": Color.BLUE})
    reloaded = Container.from_json(kb.to_json())
    assert reloaded.resolve() == []
    assert reloaded == kb
