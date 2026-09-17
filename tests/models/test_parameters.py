from pathlib import Path

import pytest

from guimauve.enums import Key, MouseDirection, ScreenArea
from guimauve.models.parameters import VNC, DefaultProperties, Parameters, Screenshot, ScreenshotActions

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


def test_parameters_round_trip():
    orig = Parameters(pause_shortcut=[Key.CTRL], sleep=1.5)
    reloaded = Parameters.from_json(orig.to_json())
    assert reloaded.resolve() == []
    assert reloaded == orig
