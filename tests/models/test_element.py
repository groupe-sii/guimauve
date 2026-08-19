import pytest

from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant, Target, TextVariant


def test_validate_does_not_silently_swallow_bounds_violation_inside_a_variant():
    # Regression: with a plain (non-discriminated) Union[ImageVariant, TextVariant], Pydantic's
    # smart union picks whichever member has fewer errors. Since strict-only checks (Bounds)
    # only raise in strict context, an ImageVariant with a strict violation used to lose to
    # TextVariant (which just ignores the unrelated keys) and get silently reclassified — the
    # violation disappeared instead of being reported. A discriminator fixes this.
    variant = ImageVariant(name="v1", path="x.png", template_confidence_threshold=42)
    element = Element(name="foo", variants=[variant])

    errors = element.validate()

    assert errors
    assert any("template_confidence_threshold" in e["loc"] and "must be" in e["msg"] for e in errors)
    # the variant itself must not have been silently reclassified as a TextVariant
    assert isinstance(element.variants[0], ImageVariant)


def test_bounds_from_mixins_apply_through_element():
    # Element inherits mouse_speed/timeout/match_index bounds from the *Params mixins.
    element = Element(name="foo", x=1, y=1, mouse_speed=-1)
    errors = element.validate()
    assert any(e["loc"] == ("mouse_speed",) and "must be >= 0" in e["msg"] for e in errors)


def test_construction_is_always_permissive():
    element = Element()
    assert element.name is None
    assert element.variants is None
    assert element._is_new is False


def test_is_new_is_a_plain_settable_private_attribute():
    element = Element()
    element._is_new = True
    assert element._is_new is True
    # not a schema field: excluded from serialization
    assert "_is_new" not in element.to_dict()


# --- has_coordinates / resolve_coordinates ---


def test_has_coordinates_false_when_nothing_set():
    assert Element().has_coordinates() is False


@pytest.mark.parametrize(
    "kwargs", [{"x": 10}, {"y": 10}, {"rel_x": 5}, {"rel_y": 5}, {"x": 10, "y": 20}]
)
def test_has_coordinates_true_when_any_coordinate_set(kwargs):
    assert Element(**kwargs).has_coordinates() is True


def test_resolve_coordinates_uses_absolute_when_set():
    element = Element(x=100, y=200)
    assert element.resolve_coordinates(mouse_x=0, mouse_y=0) == (100, 200)


def test_resolve_coordinates_uses_relative_offset_when_absolute_unset():
    element = Element(rel_x=10, rel_y=-5)
    assert element.resolve_coordinates(mouse_x=50, mouse_y=50) == (60, 45)


def test_resolve_coordinates_mixes_absolute_and_relative_per_axis():
    element = Element(x=100, rel_y=-5)
    assert element.resolve_coordinates(mouse_x=0, mouse_y=50) == (100, 45)


# --- validate_name (field-level) ---


def test_construction_with_empty_name_never_raises():
    Element(name="")
    Element(name="   ")
    Element()


@pytest.mark.parametrize("name", [None, "", "   "])
def test_validate_flags_empty_name(name):
    element = Element(name=name)
    errors = element.validate()
    assert any("must not be empty" in e["msg"] for e in errors)


def test_field_error_suppresses_cross_field_validator():
    # A field-level failure (name) stops mode="after" model validators from running at all —
    # matches sugar's original _validate_custom_rules behavior (field hooks first, full_validate
    # only if none failed). Here name is invalid AND coordinates conflict, but only the name
    # error is reported.
    element = Element(name=None, x=1, rel_x=2)
    errors = element.validate()

    assert len(errors) == 1
    assert "must not be empty" in errors[0]["msg"]


# --- cross-field rules ---


def test_validate_passes_for_a_minimal_valid_element():
    element = Element(name="foo", x=10, y=20)
    assert element.validate() == []


def test_validate_flags_x_and_rel_x_conflict():
    element = Element(name="foo", x=10, rel_x=5)
    errors = element.validate()
    assert any("absolute and a relative X" in e["msg"] for e in errors)


def test_validate_flags_both_axis_conflicts_at_once():
    element = Element(name="foo", x=10, rel_x=5, y=20, rel_y=15)
    errors = element.validate()

    assert len(errors) == 1
    assert "absolute and a relative X" in errors[0]["msg"]
    assert "absolute and a relative Y" in errors[0]["msg"]


def test_validate_flags_missing_coordinates_and_variants():
    element = Element(name="foo")
    errors = element.validate()
    assert any("must have at least coordinates or one variant" in e["msg"] for e in errors)


def test_validate_passes_with_only_a_variant_and_no_coordinates():
    element = Element(name="foo", variants=[TextVariant(name="v1", text="hello")])
    assert element.validate() == []


def test_validate_skips_target_check_when_target_is_a_list():
    element = Element(name="foo", x=1, y=1, target=[1, 2, 3])
    assert element.validate() == []


def test_validate_skips_target_check_when_target_is_unset():
    # Regression: target=None means "no override, defer to the variant's default_target at
    # runtime" (controller.py: `target_name = target or variant.default_target`) — it must not
    # be treated as a target name that fails to match any variant's targets.
    variant = ImageVariant(
        name="v1", path="x.png", targets=[Target(name="a", x=1, y=1)], default_target="a"
    )
    element = Element(name="foo", variants=[variant])
    assert element.validate() == []


def test_validate_flags_target_not_defined_in_any_variant():
    variant = ImageVariant(name="v1", path="x.png", targets=[Target(name="a", x=1, y=1)])
    element = Element(name="foo", target="missing", variants=[variant])

    errors = element.validate()
    assert any("target 'missing' is not defined in variant 'v1'" in e["msg"] for e in errors)


def test_validate_flags_target_not_defined_joins_multiple_variant_names_naturally():
    variants = [
        ImageVariant(name="a", path="a.png", targets=[Target(name="x", x=1, y=1)]),
        ImageVariant(name="b", path="b.png", targets=[Target(name="x", x=1, y=1)]),
        ImageVariant(name="c", path="c.png", targets=[Target(name="x", x=1, y=1)]),
    ]
    element = Element(name="foo", target="missing", variants=variants)

    errors = element.validate()
    assert any("in variants 'a', 'b' and 'c'" in e["msg"] for e in errors)


def test_validate_passes_when_target_is_defined_in_a_variant():
    variant = ImageVariant(name="v1", path="x.png", targets=[Target(name="a", x=1, y=1)])
    element = Element(name="foo", target="a", variants=[variant])

    assert element.validate() == []


# --- Union[ImageVariant, TextVariant] smart discrimination ---


def test_variants_union_round_trip_preserves_each_type():
    element = Element(
        name="foo",
        x=1,
        y=1,
        variants=[ImageVariant(name="img", path="x.png"), TextVariant(name="txt", text="hello")],
    )

    dumped = element.to_dict()
    loaded = Element.from_dict(dumped)

    assert isinstance(loaded.variants[0], ImageVariant)
    assert isinstance(loaded.variants[1], TextVariant)
    assert loaded.variants[0].path == "x.png"
    assert loaded.variants[1].text == "hello"
