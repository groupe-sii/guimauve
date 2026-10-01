import pytest

from guimauve.models.area import Area

# --- pure geometry: no validation, no screen needed ---


def test_geometry_dimensions():
    a = Area(top=10, left=20, right=120, bottom=60)
    assert a.width == 100
    assert a.height == 50


def test_geometry_corners():
    a = Area(top=10, left=20, right=120, bottom=60)
    assert a.tl == (20, 10)
    assert a.tr == (120, 10)
    assert a.br == (120, 60)
    assert a.bl == (20, 60)


def test_geometry_conversions():
    a = Area(top=10, left=20, right=120, bottom=60)
    assert a.as_xywh() == (20, 10, 100, 50)
    assert a.as_ltrb() == (20, 10, 120, 60)


def test_construction_is_deferred():
    # absurd values do not raise at construction; geometry still computes
    a = Area(top=99999, left=0, right=0, bottom=0)
    assert a.width == 0


# --- coordinates: non-negative, not bound to any screen ---


def test_valid_area_resolves_clean():
    assert Area(top=10, left=10, right=100, bottom=100).resolve() == []


def test_coordinates_are_not_bound_to_a_screen():
    # screen bounds are checked at runtime against the actual capture, not here
    assert Area(top=0, left=0, right=7680, bottom=4320).resolve() == []


@pytest.mark.parametrize("field", ["top", "bottom", "left", "right"])
def test_negative_coordinate_reports_field_error(field):
    coords = {"top": 10, "left": 10, "right": 100, "bottom": 100}
    coords[field] = -1
    errors = Area(**coords).resolve()
    err = next(e for e in errors if e["loc"] == (field,))
    assert err["type"] == "greater_than_equal"


# --- ordering checks (valid coordinates so field validators pass) ---


def test_top_must_be_less_than_bottom():
    errors = Area(top=100, left=10, right=100, bottom=50).resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "invalid_order"
    assert errors[0]["ctx"]["axis"] == "vertical"


def test_left_must_be_less_than_right():
    errors = Area(top=10, left=100, right=10, bottom=100).resolve()
    assert errors[0]["ctx"]["axis"] == "horizontal"


def test_both_ordering_violations_aggregate():
    errors = Area(top=100, left=100, right=10, bottom=50).resolve()
    assert {e["ctx"]["axis"] for e in errors} == {"vertical", "horizontal"}


def test_bound_failure_short_circuits_ordering():
    errors = Area(top=-1, left=100, right=10, bottom=50).resolve()
    assert all(e["type"] != "invalid_order" for e in errors)
