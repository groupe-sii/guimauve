import enum

import pytest

from guimauve.models.model import Model, ModelError


class Color(enum.Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


class Base(Model):
    name: str = ""
    tags: list = []
    color: Color = Color.RED


class Child(Model):
    items: list = []


class WithChild(Model):
    child: Child = Child()


# --- applies only given kwargs + purity ---


def test_call_applies_only_given_kwargs():
    a = Base(name="old", color=Color.RED)
    r = a(name="new")
    assert r.name == "new"
    assert r.color is Color.RED  # untouched field preserved


def test_call_returns_new_instance_and_does_not_mutate_self():
    a = Base(name="old")
    r = a(name="new")
    assert r is not a
    assert a.name == "old"
    assert r.name == "new"


def test_call_no_kwargs_returns_equal_but_distinct_copy():
    a = Base(name="x", tags=[1])
    r = a()
    assert r == a
    assert r is not a


# --- unknown kwarg ---


def test_call_unknown_kwarg_raises():
    a = Base()
    with pytest.raises(ValueError):
        a(nonexistent=1)


# --- deep isolation ---


def test_call_deep_copies_passed_value():
    a = Base()
    passed = [["x"]]  # nested mutable
    r = a(tags=passed)
    passed[0].append("y")  # mutate the inner element
    assert r.tags == [["x"]]  # deep copy isolates nested structures too


def test_call_result_isolated_from_self_untouched_fields():
    a = Base(tags=[1])
    r = a(name="x")  # tags not passed -> preserved from self
    r.tags.append(2)
    assert a.tags == [1]  # deep copy: self untouched


# --- __call__ validates ---


def test_call_coerces_valid_override():
    a = Base()
    r = a(color="GREEN")
    assert r.color is Color.GREEN
    assert a.color is not r.color or a.color is None


def test_call_raises_on_invalid_override():
    a = Base()
    with pytest.raises(ModelError):
        a(color="NOT_A_COLOR")


# --- chaining ---


def test_call_chaining_is_pure():
    base = Base(name="base")
    r = base(name="a")(color=Color.BLUE)
    assert r.name == "a"
    assert r.color is Color.BLUE
    assert base.name == "base"
    assert base.color is Color.RED


# --- deep isolation through a nested submodel field ---


def test_call_deep_copies_nested_submodel():
    a = WithChild()
    passed = Child(items=[1])
    r = a(child=passed)
    passed.items.append(2)  # mutate the passed submodel's inner list
    assert r.child.items == [1]  # deep copy isolates the submodel


# --- override tracking (overlay) ---


def test_call_records_overridden_field_and_original():
    a = Base(name="old")
    r = a(name="new")
    assert r.overridden_fields == {"name"}
    assert r._original_values == {"name": "old"}


def test_without_overrides_restores_base():
    a = Base(name="old", color=Color.RED)
    r = a(name="new")
    base = r.without_overrides()
    assert base.name == "old"
    assert base.overridden_fields == set()
    assert base._original_values == {}


def test_override_survives_internal_resolve():
    # __call__ resolves internally; the overlay must survive (private preservation).
    a = Base(name="old")
    r = a(name="new")
    assert r.overridden_fields == {"name"}  # empty if resolve wiped the private
    assert r._original_values == {"name": "old"}


def test_chained_calls_keep_first_original():
    a = Base(name="v0")
    r = a(name="v1")(name="v2")
    assert r.name == "v2"
    assert r._original_values == {"name": "v0"}  # first, not intermediate
    assert r.without_overrides().name == "v0"


def test_update_does_not_track_overlay():
    # only __call__ feeds the overlay, not update()
    a = Base(name="x")
    r = a.update(Base(name="y"))
    assert r.overridden_fields == set()
