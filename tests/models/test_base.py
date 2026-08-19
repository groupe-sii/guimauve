from enum import Enum
from typing import Annotated, Optional, Union

import pydantic
import pytest
from pydantic import field_validator, model_validator

from guimauve.models.base import Bounds, Model, ModelValidationError, raise_if_any, strict_only


class DummyEnum(Enum):
    FIRST = "first"
    SECOND = "second"


class Inner(Model):
    label: Optional[str] = None

    @field_validator("label", mode="after")
    @classmethod
    @strict_only
    def _label_not_empty(cls, v, info):
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v


class Outer(Model):
    name: Optional[str] = None
    kind: Optional[DummyEnum] = None
    mixed: Optional[Union[DummyEnum, int]] = None
    inner: Optional[Inner] = None

    @model_validator(mode="after")
    @strict_only
    def _name_required(self, info):
        if not self.name:
            raise ValueError("must not be empty")
        return self


# --- Construction is always permissive ---


def test_construction_never_raises_even_with_missing_fields():
    assert Inner().label is None
    assert Outer().name is None


def test_strict_only_validator_never_raises_at_construction():
    Inner(label=None)
    Inner(label="")
    Outer(name=None)


# --- Enum resolution by name ---


def test_enum_resolved_by_name_only_through_from_dict():
    outer = Outer.from_dict({"kind": "FIRST"})
    assert outer.kind is DummyEnum.FIRST


def test_enum_resolved_by_name_through_union_via_from_dict():
    outer = Outer.from_dict({"mixed": "SECOND"})
    assert outer.mixed is DummyEnum.SECOND

    outer = Outer.from_dict({"mixed": 42})
    assert outer.mixed == 42


def test_enum_already_a_member_is_left_untouched():
    outer = Outer(kind=DummyEnum.SECOND)
    assert outer.kind is DummyEnum.SECOND


def test_plain_construction_does_not_convert_strings_to_enum():
    # Direct Python construction expects a real enum member, not its name as a string —
    # name-based string conversion is only for loading from dict/JSON/YAML (from_dict).
    with pytest.raises(Exception):
        Outer(kind="FIRST")


# --- Dump / load round-trip ---


def test_to_dict_serializes_enum_by_name():
    outer = Outer(name="foo", kind=DummyEnum.FIRST)
    assert outer.to_dict()["kind"] == "FIRST"


def test_to_dict_not_serializable_keeps_enum_member():
    outer = Outer(name="foo", kind=DummyEnum.FIRST)
    assert outer.to_dict(serializable=False)["kind"] is DummyEnum.FIRST


@pytest.mark.parametrize("dump, load", [("to_json", "from_json"), ("to_yaml", "from_yaml")])
def test_round_trip(dump, load):
    outer = Outer(name="foo", kind=DummyEnum.SECOND, inner=Inner(label="bar"))

    dumped = getattr(outer, dump)()
    loaded = getattr(Outer, load)(dumped)

    assert loaded == outer


def test_round_trip_through_file(tmp_path):
    outer = Outer(name="foo", kind=DummyEnum.FIRST)

    path = tmp_path / "outer.yaml"
    outer.to_file(path)
    loaded = Outer.from_file(path)

    assert loaded == outer

    path = tmp_path / "outer.json"
    outer.to_file(path)
    loaded = Outer.from_file(path)

    assert loaded == outer


def test_from_file_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "outer.txt"
    path.write_text("name: foo")

    with pytest.raises(ValueError):
        Outer.from_file(path)


def test_to_file_rejects_unsupported_extension(tmp_path):
    outer = Outer(name="foo")

    with pytest.raises(ValueError):
        outer.to_file(tmp_path / "outer.txt")


# --- __call__ : copy + override ---


def test_call_returns_independent_copy_with_overrides():
    outer = Outer(name="foo", inner=Inner(label="bar"))

    copy = outer(name="baz")

    assert copy.name == "baz"
    assert outer.name == "foo"
    assert copy.inner is not outer.inner
    assert copy.inner.label == "bar"


# --- update_from : cascade "None = inherit" ---


def test_update_from_overwrite_false_self_wins_when_set():
    child = Outer(name="child")
    parent = Outer(name="parent", kind=DummyEnum.FIRST)

    merged = child.update_from(parent, overwrite=False)

    assert merged.name == "child"
    assert merged.kind is DummyEnum.FIRST
    assert "name" not in merged.overridden_fields
    assert "kind" in merged.overridden_fields


def test_update_from_overwrite_false_none_stays_none_if_parent_also_none():
    child = Outer(name="child")
    parent = Outer(name="parent")

    merged = child.update_from(parent, overwrite=False)

    assert merged.kind is None
    assert "kind" not in merged.overridden_fields


def test_update_from_overwrite_true_parent_wins_when_set():
    child = Outer(name="child", kind=DummyEnum.SECOND)
    parent = Outer(name="parent", kind=DummyEnum.FIRST)

    merged = child.update_from(parent, overwrite=True)

    assert merged.kind is DummyEnum.FIRST
    assert merged.name == "parent"
    assert "kind" in merged.overridden_fields
    assert "name" in merged.overridden_fields


def test_update_from_overwrite_true_self_wins_if_parent_unset():
    child = Outer(name="child", kind=DummyEnum.SECOND)
    parent = Outer(name="parent")

    merged = child.update_from(parent, overwrite=True)

    assert merged.kind is DummyEnum.SECOND
    assert "kind" not in merged.overridden_fields


def test_exclude_overridden_omits_inherited_values_only():
    child = Outer(name="child")
    parent = Outer(name="parent", kind=DummyEnum.FIRST)

    merged = child.update_from(parent, overwrite=False)
    dumped = merged.to_dict(exclude_overridden=True)

    assert dumped["name"] == "child"
    assert dumped["kind"] is None

    reloaded = Outer.from_dict(dumped)
    assert reloaded.kind is None


def test_without_overrides_restores_the_pre_override_value_and_clears_tracking():
    child = Outer(name="child", kind=DummyEnum.SECOND)
    parent = Outer(name="parent", kind=DummyEnum.FIRST)

    merged = child.update_from(parent, overwrite=True)
    assert merged.kind is DummyEnum.FIRST

    clean = merged.without_overrides()

    assert clean.name == "child"
    assert clean.kind is DummyEnum.SECOND  # child's own value, from before the override
    assert clean.overridden_fields == set()
    # the merged instance itself is untouched
    assert merged.kind is DummyEnum.FIRST


def test_without_overrides_survives_a_multi_step_chain():
    # default -> element -> variant: a field overridden at the first step and passed through
    # unchanged at the second must still restore to its ORIGINAL (pre-first-override) value.
    default = Outer(name="default", kind=DummyEnum.FIRST)
    element = Outer(name="element").update_from(default, overwrite=False)
    variant = Outer(name="variant").update_from(element, overwrite=False)

    assert variant.kind is DummyEnum.FIRST
    assert "kind" in variant.overridden_fields

    clean = variant.without_overrides()
    assert clean.kind is None  # variant's own original value, before any override in the chain
    assert clean.overridden_fields == set()


# --- Deferred validation ---


def test_validate_returns_empty_list_when_valid():
    outer = Outer(name="foo", inner=Inner(label="bar"))
    assert outer.validate() == []


def test_validate_returns_errors_when_invalid_without_raising():
    outer = Outer()
    errors = outer.validate()
    assert errors
    assert any("must not be empty" in e["msg"] for e in errors)


def test_validate_raise_exception_raises_with_readable_message():
    outer = Outer()

    with pytest.raises(ModelValidationError) as exc_info:
        outer.validate(raise_exception=True, context="Outer test")

    message = str(exc_info.value)
    assert "Outer test" in message
    assert "must not be empty" in message


def test_validate_raise_exception_does_not_raise_when_valid():
    outer = Outer(name="foo")
    assert outer.validate(raise_exception=True) == []


def test_validate_propagates_into_nested_models():
    outer = Outer(name="foo", inner=Inner(label=""))

    errors = outer.validate()

    assert errors
    assert any("inner" in e["loc"] for e in errors)


# --- ModelValidationError rendering ---


class BigEnum(Enum):
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"


def test_bad_enum_name_message_shows_enum_name_and_truncated_examples():
    with pytest.raises(Exception) as exc_info:

        class WithBigEnum(Model):
            value: Optional[BigEnum] = None

        WithBigEnum.from_dict({"value": "NOT_A_MEMBER"})

    message = str(exc_info.value)
    assert "BigEnum enum" in message
    assert "A, B, C, D, ..." in message
    assert ", E" not in message and ", F" not in message  # only the first 4 members, not all 6


class TwoIssues(Model):
    a: Optional[int] = None
    b: Optional[int] = None

    @model_validator(mode="after")
    @strict_only
    def _check(self, info):
        raise_if_any(
            "a is wrong" if self.a is not None else None,
            "b is wrong" if self.b is not None else None,
        )
        return self


def test_model_validation_error_splits_combined_message_into_separate_lines():
    obj = TwoIssues(a=1, b=2)
    errors = obj.validate()
    message = str(ModelValidationError(errors, context="test"))

    assert "  - a is wrong" in message
    assert "  - b is wrong" in message


def test_model_validation_error_merges_field_prefix_from_before_validator():
    # from_dict raises a raw pydantic.ValidationError (not ModelValidationError) — render it
    # through our own formatter the way the app does, to check the merge behaviour end to end.
    try:
        Outer.from_dict({"kind": "NOT_A_MEMBER"})
        message = None
    except pydantic.ValidationError as exc:
        message = str(ModelValidationError(exc.errors(), context="test"))

    assert message is not None
    assert "- kind: 'NOT_A_MEMBER' is not part of the DummyEnum enum" in message
    assert "kind: kind:" not in message  # the field name must not be duplicated


# --- _describe_error / _format_loc : direct unit tests on synthetic ErrorDetails ---
#
# These cover native Pydantic error types (missing, bool/model/string/int/float mismatches) and
# `_format_loc`'s list-index/internal-tag handling directly, rather than hunting for a real model
# construction that happens to trigger each one — the function only cares about the dict shape.


def test_describe_error_missing_field():
    error = {"type": "missing", "loc": ("x",), "msg": "Field required", "input": {}}
    message = str(ModelValidationError([error], context="test"))
    assert "- x: is required but missing" in message


def test_describe_error_unhandled_type_falls_back_to_pydantic_message():
    # Any error type without a dedicated template (e.g. a raw "enum" error from direct
    # construction, not through from_dict) just shows Pydantic's own message unmodified.
    error = {"type": "enum", "loc": ("kind",), "msg": "Input should be 1 or 2", "input": "x"}
    message = str(ModelValidationError([error], context="test"))
    assert "- kind: Input should be 1 or 2" in message


def test_describe_error_bool_parsing():
    error = {"type": "bool_parsing", "loc": ("flag",), "msg": "...", "input": 10}
    message = str(ModelValidationError([error], context="test"))
    assert "- flag: 10 is not a valid boolean" in message


def test_describe_error_model_type():
    error = {
        "type": "model_type",
        "loc": ("nested",),
        "msg": "...",
        "input": "x",
        "ctx": {"class_name": "Inner"},
    }
    message = str(ModelValidationError([error], context="test"))
    assert "- nested: 'x' is not a valid Inner" in message


def test_describe_error_string_type():
    error = {"type": "string_type", "loc": ("name",), "msg": "...", "input": 42}
    message = str(ModelValidationError([error], context="test"))
    assert "- name: 42 is not a valid string" in message


def test_describe_error_int_type():
    error = {"type": "int_type", "loc": ("count",), "msg": "...", "input": "abc"}
    message = str(ModelValidationError([error], context="test"))
    assert "- count: 'abc' is not a valid integer" in message


def test_describe_error_float_type():
    error = {"type": "float_type", "loc": ("ratio",), "msg": "...", "input": "abc"}
    message = str(ModelValidationError([error], context="test"))
    assert "- ratio: 'abc' is not a valid number" in message


def test_format_loc_indexes_list_items():
    error = {"type": "value_error", "loc": ("items", 2), "msg": "Value error, bad", "input": None}
    message = str(ModelValidationError([error], context="test"))
    assert "- items[2]: bad" in message


def test_format_loc_indexes_a_bare_leading_list_item():
    # loc's first (and only) segment is itself an index — no field name precedes it.
    error = {"type": "value_error", "loc": (0,), "msg": "Value error, bad", "input": None}
    message = str(ModelValidationError([error], context="test"))
    assert "- [0]: bad" in message


def test_format_loc_drops_internal_pydantic_tags():
    error = {
        "type": "model_type",
        "loc": ("search_area", "function-after[_ordering(), function-after[_check_bounds(), Area]]"),
        "msg": "...",
        "input": "x",
        "ctx": {"class_name": "Area"},
    }
    message = str(ModelValidationError([error], context="test"))
    assert "- search_area: 'x' is not a valid Area" in message
    assert "function-after" not in message


def test_format_loc_drops_internal_json_or_python_tags():
    # Pydantic also tags some union members with a "json-or-python[...]" segment.
    error = {
        "type": "model_type",
        "loc": ("value", "json-or-python[json=Area,python=Area]"),
        "msg": "...",
        "input": "x",
        "ctx": {"class_name": "Area"},
    }
    message = str(ModelValidationError([error], context="test"))
    assert "- value: 'x' is not a valid Area" in message
    assert "json-or-python" not in message


# --- Bounds metadata (Annotated) ---


class WithBounds(Model):
    speed: Annotated[Optional[float], Bounds(min=0)] = None
    ratio: Annotated[Optional[float], Bounds(min=0, max=1)] = None
    unbounded: Optional[float] = None


def test_get_bounds_reads_annotated_metadata():
    assert WithBounds.get_bounds("speed") == Bounds(min=0)
    assert WithBounds.get_bounds("ratio") == Bounds(min=0, max=1)
    assert WithBounds.get_bounds("unbounded") is None


def test_bounds_metadata_is_inert_at_construction():
    # Pydantic never enforces it on its own — construction stays permissive.
    WithBounds(speed=-5, ratio=42)


def test_validate_flags_out_of_bounds_values():
    # Bounds checking is a per-field validator: violations on different fields are independent
    # and all reported together, never swallowed by one another.
    obj = WithBounds(speed=-5, ratio=1.5)
    errors = obj.validate()

    assert len(errors) == 2
    assert any(e["loc"] == ("speed",) and "must be >= 0" in e["msg"] for e in errors)
    assert any(e["loc"] == ("ratio",) and "must be <= 1" in e["msg"] for e in errors)


def test_validate_passes_within_bounds():
    obj = WithBounds(speed=10, ratio=0.5)
    assert obj.validate() == []


def test_validate_ignores_unset_bounded_fields():
    assert WithBounds().validate() == []
