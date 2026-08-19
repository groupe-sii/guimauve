import pytest

from guimauve.models import area as area_module
from guimauve.models.area import Area


@pytest.fixture(autouse=True)
def fixed_screen_size(monkeypatch):
    # Deterministic 1920x1080 "screen" regardless of the machine actually running the tests.
    monkeypatch.setattr(area_module, "get_screen_size", lambda: (1920, 1080))


def test_construction_never_validates_bounds_or_ordering():
    # top >= bottom and out-of-screen values: construction still succeeds (deferred validation).
    Area(top=500, left=500, right=100, bottom=100)


def test_properties():
    area = Area(top=10, left=20, right=120, bottom=60)

    assert area.width == 100
    assert area.height == 50
    assert area.tl == (20, 10)
    assert area.tr == (120, 10)
    assert area.br == (120, 60)
    assert area.bl == (20, 60)
    assert area.as_xywh() == (20, 10, 100, 50)
    assert area.as_ltrb() == (20, 10, 120, 60)


def test_validate_passes_for_a_sane_area():
    area = Area(top=10, left=20, right=120, bottom=60)
    assert area.validate() == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"top": -1, "left": 0, "right": 100, "bottom": 100},
        {"top": 0, "left": -1, "right": 100, "bottom": 100},
        {"top": 0, "left": 0, "right": 2000, "bottom": 100},
        {"top": 2000, "left": 0, "right": 100, "bottom": 100},
    ],
)
def test_validate_flags_out_of_screen_bounds(kwargs):
    area = Area(**kwargs)
    errors = area.validate()
    assert errors


def test_validate_flags_top_not_before_bottom():
    area = Area(top=100, left=0, right=100, bottom=50)
    errors = area.validate()
    assert any("top must be less than bottom" in e["msg"] for e in errors)


def test_validate_flags_left_not_before_right():
    area = Area(top=0, left=100, right=50, bottom=100)
    errors = area.validate()
    assert any("left must be less than right" in e["msg"] for e in errors)


def test_validate_flags_both_orderings_at_once():
    # Regression: both violations must be reported in a single .validate() call, not just the
    # first one — model_validator methods on the same class run sequentially and stop at the
    # first that raises, so both issues must be collected inside one validator.
    area = Area(top=100, left=100, right=50, bottom=50)
    errors = area.validate()

    assert len(errors) == 1
    assert "top must be less than bottom" in errors[0]["msg"]
    assert "left must be less than right" in errors[0]["msg"]
