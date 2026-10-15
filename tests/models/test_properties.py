import pytest

from guimauve.enums import ScreenArea
from guimauve.models.area import Area
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters
from guimauve.models.properties import ElementProperties, LocateProperties

# === LocateProperties ===

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


def test_area_as_dict_is_accepted():
    p = LocateProperties(search_area={"top": 0, "left": 0, "right": 100, "bottom": 100})
    assert p.resolve() == []
    assert isinstance(p.search_area, Area)


def test_area_as_instance_is_accepted():
    area = Area(top=0, left=0, right=100, bottom=100)
    p = LocateProperties(search_area=area)
    assert p.resolve() == []
    assert isinstance(p.search_area, Area)


def test_invalid_area_surfaces_its_own_error():
    # an out-of-order Area still gets validated through the union
    p = LocateProperties(search_area={"top": 100, "left": 0, "right": 100, "bottom": 50})
    errors = p.resolve()
    # the Area branch reports its ordering error; assert loosely (union loc is noisy)
    assert any(e["type"] == "invalid_order" and e["loc"][0] == "search_area" for e in errors)


# --- None is allowed (Optional) ---


def test_search_area_none_is_valid():
    assert LocateProperties(search_area=None).resolve() == []


# === ElementProperties: screen ===


@pytest.mark.parametrize("screen", [None, 0, 1, 3, [2], [1, 3]])
def test_screen_accepts_a_screen_or_a_list_of_screens(screen):
    p = ElementProperties(screen=screen)
    assert p.resolve() == []
    assert p.screen == screen


@pytest.mark.parametrize(
    ("screen", "error_type"),
    [
        (-1, "screen_negative"),
        ([], "screen_empty"),
        ([0, 1], "screen_in_list"),
        ([1, -2], "screen_in_list"),
        ([1, 3, 1], "duplicate_screen"),
    ],
)
def test_screen_rejects_invalid_values_with_a_single_error(screen, error_type):
    [error] = ElementProperties(screen=screen).resolve()
    assert error["type"] == error_type
    assert error["loc"] == ("screen",)


def test_screen_defaults_to_the_primary_screen():
    assert Parameters().default.screen == 1


def test_element_screen_falls_back_to_the_default():
    default = Parameters().default
    assert Element(name="e").update(default, overwrite=False).screen == 1
    assert Element(name="e", screen=[1, 2]).update(default, overwrite=False).screen == [1, 2]
