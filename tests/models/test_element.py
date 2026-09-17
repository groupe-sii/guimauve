from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant

# --- pure methods: no validation, no resolve needed ---


def test_has_coordinates_true_when_any_set():
    assert Element(x=5).has_coordinates()
    assert Element(rel_y=3).has_coordinates()


def test_has_coordinates_false_when_all_none():
    assert not Element().has_coordinates()


def test_resolve_coordinates_absolute_wins():
    assert Element(x=100, y=200).resolve_coordinates(0, 0) == (100, 200)


def test_resolve_coordinates_relative_adds_to_mouse():
    assert Element(rel_x=10, rel_y=-5).resolve_coordinates(50, 50) == (60, 45)


def test_resolve_coordinates_mixed_absolute_and_relative():
    # absolute x, relative y
    assert Element(x=100, rel_y=5).resolve_coordinates(0, 30) == (100, 35)


def test_private_attrs_have_defaults_after_construction():
    e = Element(x=5)
    assert e.alias is None
    assert e.is_new is False


# --- field validator: name ---


def test_name_none_is_allowed():
    # regression guard: an unnamed element (located by coords) must be valid
    assert Element(x=5).resolve() == []


def test_name_whitespace_is_rejected():
    errors = Element(name="   ", x=5).resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "empty"
    assert errors[0]["loc"] == ("name",)


def test_name_valid_passes():
    assert Element(name="button", x=5).resolve() == []


# --- model checks: coordinate conflicts (aggregated, ctx.axis) ---


def test_x_conflict_reports_axis_x():
    errors = Element(x=1, rel_x=1).resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "coordinate_conflict"
    assert errors[0]["ctx"]["axis"] == "x"


def test_y_conflict_reports_axis_y():
    errors = Element(y=1, rel_y=1).resolve()
    assert errors[0]["ctx"]["axis"] == "y"


def test_both_axis_conflicts_aggregate():
    errors = Element(x=1, rel_x=1, y=1, rel_y=1).resolve()
    assert {e["ctx"]["axis"] for e in errors} == {"x", "y"}


# --- model checks: must have a locator ---


def test_no_locator_when_empty():
    errors = Element().resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "no_locator"


def test_locator_satisfied_by_coordinates():
    assert Element(x=5).resolve() == []


def test_name_error_short_circuits_model_checks():
    # a field error suppresses the model_validator entirely
    errors = Element(name="  ").resolve()  # empty name AND no locator
    assert [e["type"] for e in errors] == ["empty"]  # no_locator NOT present


# --- model checks: variants (adjust to your real variant constructors) ---


def test_target_not_defined_in_variants(real_file):
    v = ImageVariant(name="v1", path=real_file, targets=[])  # no target named "go"
    e = Element(target="go", variants={"v1": v})
    errors = e.resolve()
    assert any(err["type"] == "target_not_found" for err in errors)
    err = next(err for err in errors if err["type"] == "target_not_found")
    assert err["ctx"]["target"] == "go"
    assert err["ctx"]["missing"] == ["v1"]
