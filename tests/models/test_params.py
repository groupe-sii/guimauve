import pytest

from guimauve.models.params import ElementParams, ImageParams, MatchParams, MouseParams, TextParams


def test_mouse_speed_zero_is_valid_but_negative_is_not():
    assert MouseParams(mouse_speed=0).validate() == []

    errors = MouseParams(mouse_speed=-1).validate()
    assert any(e["loc"] == ("mouse_speed",) and "must be >= 0" in e["msg"] for e in errors)


def test_construction_never_validates_bounds():
    MouseParams(mouse_speed=-100)  # must not raise
    ImageParams(template_confidence_threshold=42)  # must not raise


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_template_confidence_threshold_must_be_a_ratio(value):
    errors = ImageParams(template_confidence_threshold=value).validate()
    assert any(e["loc"] == ("template_confidence_threshold",) and "must be" in e["msg"] for e in errors)


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_template_confidence_threshold_accepts_full_ratio_range(value):
    assert ImageParams(template_confidence_threshold=value).validate() == []


@pytest.mark.parametrize(
    "field, value",
    [
        ("feature_n_features", 5),
        ("feature_n_features", 10000),
        ("feature_contrast_threshold", 0.0),
        ("feature_edge_threshold", 0),
        ("feature_sigma", 0.1),
        ("feature_lowe_ratio", 1.0),
        ("feature_min_points", 3),
        ("feature_ransac_threshold", 0.5),
        ("feature_ratio_tolerance", 0.0),
        ("feature_size_tolerance", 0.0),
        ("ocr_confidence_threshold", 1.5),
    ],
)
def test_feature_and_ocr_thresholds_flag_out_of_range_values(field, value):
    errors = ImageParams(**{field: value}).validate()
    assert any(e["loc"] == (field,) for e in errors)


def test_text_confidence_threshold_must_be_a_ratio():
    errors = TextParams(text_confidence_threshold=1.5).validate()
    assert any(e["loc"] == ("text_confidence_threshold",) and "must be" in e["msg"] for e in errors)


def test_match_index_must_be_within_gui_range():
    assert MatchParams(match_index=500).validate() == []

    errors = MatchParams(match_index=-1).validate()
    assert any(e["loc"] == ("match_index",) and "must be >= 0" in e["msg"] for e in errors)


def test_timeout_must_not_be_negative():
    assert ElementParams(timeout=0).validate() == []

    errors = ElementParams(timeout=-1).validate()
    assert any(e["loc"] == ("timeout",) and "must be >= 0" in e["msg"] for e in errors)


def test_bounds_are_reachable_via_the_mixin_class():
    assert MouseParams.get_bounds("mouse_speed").min == 0
    assert ImageParams.get_bounds("template_confidence_threshold").max == 1.0
