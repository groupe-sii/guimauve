import pytest

from guimauve.models.area import Area

SCREEN = (1920, 1080)


@pytest.fixture
def screen(monkeypatch):
    # patch where the name is looked up (inside area.py), not where it's defined
    monkeypatch.setattr("guimauve.models.area.get_screen_size", lambda: SCREEN)
    return SCREEN


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


# --- screen bounds (need the mocked screen) ---


def test_within_bounds_resolves_clean(screen):
    assert Area(top=10, left=10, right=100, bottom=100).resolve() == []


def test_bounds_are_inclusive(screen):
    w, h = screen
    a = Area(top=0, left=0, right=w, bottom=h)
    # ordering is valid (0 < w, 0 < h), and 0..max are accepted
    assert a.resolve() == []


@pytest.mark.parametrize(
    "field,value,loc,expected_max",
    [
        ("top", -1, ("top",), 1080),  # vertical -> height
        ("bottom", 1081, ("bottom",), 1080),
        ("left", -1, ("left",), 1920),  # horizontal -> width
        ("right", 1921, ("right",), 1920),
    ],
)
def test_out_of_bounds_reports_field_error(screen, field, value, loc, expected_max):
    coords = {"top": 10, "left": 10, "right": 100, "bottom": 100}
    coords[field] = value
    errors = Area(**coords).resolve()
    err = next(e for e in errors if e["loc"] == loc)
    assert err["type"] == "out_of_bounds"
    assert err["ctx"] == {"min": 0, "max": expected_max}


# --- ordering checks (in-bounds so field validators pass) ---


def test_top_must_be_less_than_bottom(screen):
    errors = Area(top=100, left=10, right=100, bottom=50).resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "invalid_order"
    assert errors[0]["ctx"]["axis"] == "vertical"


def test_left_must_be_less_than_right(screen):
    errors = Area(top=10, left=100, right=10, bottom=100).resolve()
    assert errors[0]["ctx"]["axis"] == "horizontal"


def test_both_ordering_violations_aggregate(screen):
    errors = Area(top=100, left=100, right=10, bottom=50).resolve()
    assert {e["ctx"]["axis"] for e in errors} == {"vertical", "horizontal"}


def test_bound_failure_short_circuits_ordering(screen):
    errors = Area(top=99999, left=100, right=10, bottom=50).resolve()
    assert all(e["type"] != "invalid_order" for e in errors)
