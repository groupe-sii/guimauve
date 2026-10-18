import pytest

from guimauve.gui.element_editor_next.schema import FIELDS, FIXED_POSITION_KEYS, SECTIONS, Level
from guimauve.models.properties import (
    ElementProperties,
    ImageProperties,
    LocateProperties,
    MatchProperties,
    MouseProperties,
    TextProperties,
)
from guimauve.models.variant import ImageVariant, TextVariant

PROPERTY_MODELS = (
    ElementProperties,
    LocateProperties,
    MouseProperties,
    ImageProperties,
    TextProperties,
    MatchProperties,
)


def test_every_property_has_exactly_one_descriptor():
    properties = {key for model in PROPERTY_MODELS for key in model.model_fields} | set(FIXED_POSITION_KEYS)
    keys = [field.key for section in SECTIONS for field in section.fields]

    assert len(keys) == len(set(keys))
    assert set(keys) == properties


def test_sections_follow_the_specification_order():
    assert [section.key for section in SECTIONS] == [
        "general",
        "where_to_search",
        "image_detection",
        "text_detection",
        "multiple_matches",
        "mouse",
        "fixed_position",
    ]


def test_detection_sections_depend_on_variant_kind():
    kinds = {section.key: section.variant_kind for section in SECTIONS}

    assert kinds["image_detection"] is ImageVariant
    assert kinds["text_detection"] is TextVariant
    assert kinds["general"] is None


@pytest.mark.parametrize(
    ("key", "levels"),
    [
        ("timeout", {Level.ELEMENT}),
        ("screen", {Level.ELEMENT}),
        ("x", {Level.ELEMENT}),
        ("search_area", {Level.ELEMENT, Level.IMAGE_VARIANT, Level.TEXT_VARIANT}),
        ("use_template", {Level.ELEMENT, Level.IMAGE_VARIANT}),
        ("text_fidelity", {Level.ELEMENT, Level.TEXT_VARIANT}),
    ],
)
def test_levels_are_read_from_models(key, levels):
    assert FIELDS[key].levels == levels


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("mouse_speed", (0, 5000)),
        ("feature_sigma", (0.5, 3.0)),
        ("timeout", (0, None)),
        ("find_all", (None, None)),
    ],
)
def test_bounds_are_read_from_models(key, expected):
    assert FIELDS[key].bounds == expected


def test_feature_settings_are_the_nine_advanced_fields():
    advanced = [field.key for field in FIELDS.values() if field.advanced]

    assert len(advanced) == 9
    assert all(key.startswith("feature_") for key in advanced)


@pytest.mark.parametrize("enabled", [True, False])
def test_method_settings_are_hidden_when_method_is_disabled(enabled):
    values = {"use_template": enabled, "use_feature": enabled, "use_ocr": enabled}

    for key in ("template_confidence_threshold", "feature_sigma", "ocr_fidelity"):
        assert FIELDS[key].visible(values) is enabled
    assert FIELDS["use_feature"].visible(values)


@pytest.mark.parametrize("axis", FIXED_POSITION_KEYS)
def test_detection_fields_have_no_effect_with_fixed_position(axis):
    values = {axis: 10}

    assert not FIELDS["template_confidence_threshold"].effective(values)
    assert not FIELDS["search_area"].effective(values)
    assert FIELDS["mouse_speed"].effective(values)
    assert FIELDS["screen"].effective(values)


def test_detection_fields_are_effective_without_fixed_position():
    assert all(field.effective({}) for field in FIELDS.values())


def test_toggles_are_the_detection_methods():
    toggles = {field.key for field in FIELDS.values() if field.toggle}
    assert toggles == {"use_template", "use_feature", "use_ocr"}
