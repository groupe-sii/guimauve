import pytest

from guimauve.enums import ScreenArea
from guimauve.models.area import Area
from guimauve.models.properties import LocateProperties

SCREEN = (1920, 1080)


@pytest.fixture
def screen(monkeypatch):
    monkeypatch.setattr("guimauve.models.area.get_screen_size", lambda: SCREEN)
    return SCREEN


# --- the enum branch: ScreenArea by name ---


def test_screen_area_name_is_coerced():
    p = LocateProperties(search_area="FULL")  # adapt "FULL" to a real ScreenArea member
    assert p.resolve() == []
    assert p.search_area is ScreenArea.FULL


def test_invalid_screen_area_name_is_rejected():
    p = LocateProperties(search_area="NOPE")
    errors = p.resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "enum_name"
    assert errors[0]["loc"] == ("search_area",)


# --- the Area branch: must NOT be hijacked by enum coercion (regression) ---


def test_area_as_dict_is_accepted(screen):
    p = LocateProperties(search_area={"top": 0, "left": 0, "right": 100, "bottom": 100})
    assert p.resolve() == []
    assert isinstance(p.search_area, Area)


def test_area_as_instance_is_accepted(screen):
    area = Area(top=0, left=0, right=100, bottom=100)
    p = LocateProperties(search_area=area)
    assert p.resolve() == []
    assert isinstance(p.search_area, Area)


def test_invalid_area_surfaces_its_own_error(screen):
    # an out-of-order Area still gets validated through the union
    p = LocateProperties(search_area={"top": 100, "left": 0, "right": 100, "bottom": 50})
    errors = p.resolve()
    # the Area branch reports its ordering error; assert loosely (union loc is noisy)
    assert any(e["type"] == "invalid_order" and e["loc"][0] == "search_area" for e in errors)


# --- None is allowed (Optional) ---


def test_search_area_none_is_valid():
    assert LocateProperties(search_area=None).resolve() == []
