from pathlib import Path

import pytest

from guimauve.enums import Key, MatchSort, MouseDirection, OcrFidelity, ScreenArea
from guimauve.models.parameters.parameters import DefaultParams, Parameters
from guimauve.models.parameters.screenshot import Screenshot, ScreenshotActions
from guimauve.models.parameters.vnc import VNC


def test_bounds_violation_not_swallowed_by_an_unrelated_sibling_field_error():
    # Regression: sleep's Bounds violation used to disappear whenever a completely unrelated
    # field (debug_elements) also failed, because bounds checking used to be a model-level
    # validator that only runs once every field has already validated successfully.
    parameters = Parameters()
    parameters.sleep = -2
    parameters.debug_elements = 10
    parameters.default.mouse_speed = -1

    errors = parameters.validate()

    assert any(e["loc"] == ("sleep",) and "must be >= 0" in e["msg"] for e in errors)
    assert any("valid boolean" in e["msg"] for e in errors)
    assert any(e["loc"] == ("default", "mouse_speed") and "must be >= 0" in e["msg"] for e in errors)


def test_default_params_bounds_inherited_from_mixins_still_apply():
    # DefaultParams supplies its real defaults via a before-validator rather than re-annotating
    # each field, so the Bounds metadata declared once on the mixins is never overridden away.
    assert DefaultParams().validate() == []

    errors = DefaultParams(template_confidence_threshold=42).validate()
    assert any(e["loc"] == ("template_confidence_threshold",) and "must be" in e["msg"] for e in errors)


def test_default_params_bounds_reachable_directly_on_the_class():
    assert DefaultParams.get_bounds("template_confidence_threshold").max == 1.0


def test_default_params_documented_defaults():
    default = DefaultParams()

    assert default.search_area is ScreenArea.FULL
    assert default.mouse_direction is MouseDirection.STRAIGHT
    assert default.use_template is True
    assert default.template_confidence_threshold == 0.95
    assert default.use_feature is False
    assert default.use_ocr is False
    assert default.ocr_fidelity is OcrFidelity.FAST
    assert default.text_fidelity is OcrFidelity.FAST
    assert default.match_index == 0
    assert default.match_sort is MatchSort.XY_POSITION
    assert default.timeout == 5
    assert default.find_all is False


# --- No shared mutable state across instances (the original concern) ---


def test_parameters_default_and_screenshot_are_independent_per_instance():
    a = Parameters()
    b = Parameters()

    assert a.default is not b.default
    assert a.screenshot is not b.screenshot
    assert a.screenshot.on is not b.screenshot.on

    a.default.use_template = False
    a.screenshot.enable = True
    a.screenshot.on.locate = False

    assert b.default.use_template is True
    assert b.screenshot.enable is False
    assert b.screenshot.on.locate is True


def test_parameters_pause_shortcut_list_is_independent_per_instance():
    a = Parameters()
    b = Parameters()

    assert a.pause_shortcut is not b.pause_shortcut

    a.pause_shortcut.append(Key.ESC)

    assert Key.ESC not in b.pause_shortcut
    assert b.pause_shortcut == [Key.CTRL, Key.SHIFT, Key.ALT]


# --- Screenshot / Path serialization ---


def test_screenshot_defaults():
    screenshot = Screenshot()
    assert screenshot.enable is False
    assert screenshot.folder == Path("screenshots")
    assert isinstance(screenshot.on, ScreenshotActions)
    assert screenshot.on.locate is True


def test_screenshot_limit_must_not_be_negative():
    screenshot = Screenshot(limit=-1)
    errors = screenshot.validate()
    assert any(e["loc"] == ("limit",) and "must be >= 0" in e["msg"] for e in errors)


def test_screenshot_limit_construction_never_validates():
    Screenshot(limit=-1)  # must not raise


def test_screenshot_folder_path_round_trips_through_dump_and_load():
    screenshot = Screenshot(folder=Path("custom/dir"))

    dumped = screenshot.to_dict()
    assert dumped["folder"] == "custom/dir" or dumped["folder"] == str(Path("custom/dir"))

    # to_json/to_yaml must not crash on the Path default
    screenshot.to_json()
    screenshot.to_yaml()

    loaded = Screenshot.from_dict(dumped)
    assert str(loaded.folder) == str(Path("custom/dir"))


# --- VNC ---


def test_vnc_requires_host():
    with pytest.raises(Exception):
        VNC()

    VNC(host="10.0.0.1")


def test_vnc_construction_never_validates_display_or_port():
    VNC(host="10.0.0.1")  # neither display nor port: construction must not raise


def test_vnc_validate_requires_display_or_port():
    vnc = VNC(host="10.0.0.1")
    errors = vnc.validate()
    assert any("display or a port" in e["msg"] for e in errors)


@pytest.mark.parametrize("kwargs", [{"display": 1}, {"port": 5900}, {"display": 1, "port": 5900}])
def test_vnc_validate_passes_with_display_or_port(kwargs):
    vnc = VNC(host="10.0.0.1", **kwargs)
    assert vnc.validate() == []


def test_vnc_display_must_not_be_negative():
    vnc = VNC(host="10.0.0.1", display=-1)
    errors = vnc.validate()
    assert any(e["loc"] == ("display",) and "must be >= 0" in e["msg"] for e in errors)


@pytest.mark.parametrize("port", [0, -1, 70000])
def test_vnc_port_must_be_in_valid_tcp_range(port):
    vnc = VNC(host="10.0.0.1", port=port)
    errors = vnc.validate()
    assert any(e["loc"] == ("port",) and "must be" in e["msg"] for e in errors)


def test_vnc_construction_never_validates_bounds():
    VNC(host="10.0.0.1", display=-1, port=999999)  # must not raise


# --- Parameters.sleep ---


def test_parameters_construction_never_validates_sleep():
    Parameters(sleep=-5)  # construction must not raise


def test_parameters_validate_flags_negative_sleep():
    parameters = Parameters(sleep=-5)
    errors = parameters.validate()
    assert any(e["loc"] == ("sleep",) and "must be >= 0" in e["msg"] for e in errors)


@pytest.mark.parametrize("sleep", [0, 1, 2.5])
def test_parameters_validate_passes_for_non_negative_sleep(sleep):
    parameters = Parameters(sleep=sleep)
    assert parameters.validate() == []


# --- Enum-by-name round trip through a nested DefaultParams ---


def test_default_params_enum_round_trip_through_parameters():
    parameters = Parameters(default=DefaultParams(ocr_fidelity=OcrFidelity.ACCURATE))

    dumped = parameters.to_dict()
    assert dumped["default"]["ocr_fidelity"] == "ACCURATE"

    loaded = Parameters.from_dict(dumped)
    assert loaded.default.ocr_fidelity is OcrFidelity.ACCURATE
