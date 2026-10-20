from pathlib import Path

import pytest

from guimauve.enums import Key, MouseDirection, ScreenArea
from guimauve.models.element import Element
from guimauve.models.parameters import (
    VNC,
    Checks,
    DefaultProperties,
    Parameters,
    ScreenCheck,
    Screenshot,
    ScreenshotActions,
)

# ============ VNC ============


def test_host_required_missing():
    assert any(e["type"] == "missing" and e["loc"] == ("host",) for e in VNC(display=0).resolve())


@pytest.mark.parametrize("value", ["", "   "])
def test_host_blank_is_rejected(value):
    errors = VNC(host=value, display=0).resolve()
    assert errors[0]["type"] == "empty"
    assert errors[0]["loc"] == ("host",)


def test_valid_with_port():
    assert VNC(host="pc", port=5900).resolve() == []


def test_valid_with_display():
    assert VNC(host="pc", display=1).resolve() == []


def test_display_zero_counts_as_specified():
    # display=0 is not None -> satisfies the rule (guards against a truthiness check)
    assert VNC(host="pc", display=0).resolve() == []


def test_no_endpoint_when_neither():
    errors = VNC(host="pc").resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "no_endpoint"
    assert errors[0]["loc"] == ()


def test_host_error_short_circuits_endpoint_check():
    assert [e["type"] for e in VNC(host="   ").resolve()] == ["empty"]


@pytest.mark.parametrize("port,expected", [(0, "greater_than"), (65536, "less_than_equal")])
def test_port_out_of_range(port, expected):
    assert any(e["type"] == expected for e in VNC(host="pc", port=port).resolve())


def test_display_negative_rejected():
    assert any(e["type"] == "greater_than_equal" for e in VNC(host="pc", display=-1).resolve())


# ============ Screenshot / ScreenshotActions ============


def test_screenshot_defaults():
    s = Screenshot()
    assert s.resolve() == []
    assert s.enable is False
    assert s.folder == Path("screenshots")
    assert s.limit is None


def test_screenshot_limit_must_be_positive():
    assert any(e["type"] == "greater_than" for e in Screenshot(limit=0).resolve())


def test_screenshot_limit_valid():
    assert Screenshot(limit=5).resolve() == []


def test_screenshot_custom_folder_accepted():
    assert Screenshot(folder="custom").resolve() == []


def test_screenshot_actions_defaults_all_true():
    a = ScreenshotActions()
    assert a.resolve() == []
    assert a.locate is True
    assert a.click is True


def test_screenshot_actions_override():
    a = ScreenshotActions(click=False)
    assert a.click is False
    assert a.locate is True


def test_screenshot_nested_on_override():
    s = Screenshot(on=ScreenshotActions(click=False))
    assert s.resolve() == []
    assert s.on.click is False


# ============ Parameters ============


def test_default_is_prefilled_before_resolve():
    p = Parameters()
    assert p.default.search_area is ScreenArea.FULL
    assert p.default.use_template is True
    assert p.default.template_confidence_threshold == 0.95


def test_default_still_filled_after_resolve():
    p = Parameters()
    assert p.resolve() == []
    assert p.default.mouse_direction is MouseDirection.STRAIGHT


def test_default_instances_are_independent():
    assert Parameters().default is not Parameters().default


def test_default_constraint_preserved():
    # inherited ge/le must still apply on the default params
    p = Parameters(default=DefaultProperties(template_confidence_threshold=2.0))
    assert any(e["type"] == "less_than_equal" for e in p.resolve())


def test_pause_shortcut_accepts_names():
    p = Parameters(pause_shortcut=["CTRL", "ALT"])
    assert p.resolve() == []
    assert p.pause_shortcut == [Key.CTRL, Key.ALT]


def test_pause_shortcut_dumps_by_name():
    p = Parameters(pause_shortcut=[Key.CTRL, Key.SHIFT])
    assert p.to_dict(json_mode=True)["pause_shortcut"] == ["CTRL", "SHIFT"]


def test_sleep_zero_is_allowed():
    assert Parameters(sleep=0.0).resolve() == []


def test_sleep_negative_rejected():
    assert any(e["type"] == "greater_than_equal" for e in Parameters(sleep=-1.0).resolve())


def test_execution_mode_invalid():
    assert any(e["type"] == "literal_error" for e in Parameters(execution_mode="remote").resolve())


def test_vnc_dict_resolves_to_vnc():
    p = Parameters(vnc={"host": "pc", "port": 5900})
    assert p.resolve() == []
    assert isinstance(p.vnc, VNC)


def test_vnc_error_surfaces_with_nested_loc():
    p = Parameters(vnc={"host": ""})
    errors = p.resolve()
    assert any(e["type"] == "empty" and e["loc"][0] == "vnc" for e in errors)


def test_vnc_error_when_vnc_execution_and_vnc_is_none():
    p = Parameters(execution_mode="vnc")
    errors = p.resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "vnc_config_missing"
    assert errors[0]["loc"] == ()


def test_vnc_execution_with_vnc_is_valid():
    p = Parameters(execution_mode="vnc", vnc=VNC(host="pc", port=5900))
    assert p.resolve() == []


def test_default_timeout_none_rejected():
    errors = Parameters(default={"timeout": None}).resolve()
    assert len(errors) == 1
    assert errors[0]["type"] == "timeout_required"
    assert errors[0]["loc"] == ("default",)


def test_element_timeout_none_still_allowed():
    assert Element(name="button", x=0, y=0).resolve() == []


def test_parameters_round_trip():
    orig = Parameters(pause_shortcut=[Key.CTRL], sleep=1.5)
    reloaded = Parameters.from_json(orig.to_json())
    assert reloaded.resolve() == []
    assert reloaded == orig


# ============ ScreenCheck ============


def test_screen_check_defaults_to_primary_screen():
    assert ScreenCheck(size=(1920, 1080)).number == 1


@pytest.mark.parametrize("fields", [{"size": (1920, 1080)}, {"scaling": 100}, {"size": (1920, 1080), "scaling": 125}])
def test_screen_check_valid(fields):
    assert ScreenCheck(**fields).resolve() == []


def test_screen_check_needs_size_or_scaling():
    assert [e["type"] for e in ScreenCheck(number=2).resolve()] == ["nothing_to_check"]


@pytest.mark.parametrize(
    "fields", [{"number": 0, "scaling": 100}, {"size": (0, 1080)}, {"size": (1920, -1)}, {"scaling": 0}]
)
def test_screen_check_values_must_be_positive(fields):
    assert ScreenCheck(**fields).resolve() != []


# ============ Checks ============


def test_checks_disabled_by_default():
    c = Checks()
    assert c.screen is None
    assert c.datasets is False


def test_parameters_has_default_checks():
    assert Parameters().checks == Checks()


@pytest.mark.parametrize("single", [{"size": [1920, 1080]}, ScreenCheck(size=(1920, 1080))])
def test_single_screen_is_wrapped_in_a_list(single):
    c = Checks(screen=single)
    assert c.resolve() == []
    assert c.screen == [ScreenCheck(number=1, size=(1920, 1080))]


def test_several_screens():
    c = Checks(screen=[{"number": 1, "size": [1920, 1080]}, {"number": 2, "size": [1280, 720], "scaling": 75}])
    assert c.resolve() == []
    assert [s.number for s in c.screen] == [1, 2]


def test_screen_empty_list_rejected():
    assert [e["type"] for e in Checks(screen=[]).resolve()] == ["empty_screen"]


def test_screen_numbers_must_be_unique():
    errors = Checks(screen=[{"number": 2, "scaling": 100}, {"number": 2, "size": [1, 1]}]).resolve()
    assert [e["type"] for e in errors] == ["duplicate_screen"]


def test_screens_without_number_are_duplicates():
    # both default to screen 1
    errors = Checks(screen=[{"size": [1920, 1080]}, {"scaling": 100}]).resolve()
    assert [e["type"] for e in errors] == ["duplicate_screen"]


@pytest.mark.parametrize("datasets", [True, False, ["login"], ["login", "main_menu"]])
def test_datasets_valid_values(datasets):
    assert Checks(datasets=datasets).resolve() == []


def test_datasets_empty_list_rejected():
    assert [e["type"] for e in Checks(datasets=[]).resolve()] == ["empty_datasets"]


def test_datasets_invalid_names_rejected():
    errors = Checks(datasets=["login", "Bad", "class"]).resolve()
    assert [e["type"] for e in errors] == ["bad_dataset_name"]
    assert "'Bad'" in errors[0]["msg"]
    assert "'class'" in errors[0]["msg"]
