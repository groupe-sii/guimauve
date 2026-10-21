import json
import logging

import pytest

import guimauve.controller as controller_module
from guimauve.checks import EnvironmentCheckError
from guimauve.drivers.driver import Screen
from guimauve.drivers.pausable_driver import PausableDriver
from guimauve.enums import Key
from guimauve.models.model import ModelError
from guimauve.models.parameters import Parameters
from guimauve.storage.workspace import DataWorkspace


def test_defaults_when_no_parameters(make_controller):
    assert make_controller().parameters == Parameters()


def test_accepts_parameters_instance(make_controller):
    parameters = Parameters(sleep=0.5)
    assert make_controller(parameters=parameters).parameters is parameters


def test_accepts_dict(make_controller):
    assert make_controller(parameters={"sleep": 0.5}).parameters.sleep == 0.5


@pytest.mark.parametrize("as_str", [False, True])
def test_accepts_json_file(make_controller, tmp_path, as_str):
    path = tmp_path / "parameters.json"
    path.write_text(json.dumps({"sleep": 0.5}))
    assert make_controller(parameters=str(path) if as_str else path).parameters.sleep == 0.5


def test_accepts_yaml_file(make_controller, tmp_path):
    path = tmp_path / "parameters.yaml"
    path.write_text("sleep: 0.5\n")
    assert make_controller(parameters=path).parameters.sleep == 0.5


@pytest.mark.parametrize("parameters", [{"sleep": -1}, {"execution_mode": "vnc"}])
def test_invalid_parameters_raise_model_error(make_controller, parameters):
    with pytest.raises(ModelError):
        make_controller(parameters=parameters)


def test_unsupported_type_raises_type_error(make_controller):
    with pytest.raises(TypeError):
        make_controller(parameters=42)


def test_driver_is_wrapped_in_pausable_driver(controller, fake_driver):
    assert isinstance(controller._driver, PausableDriver)
    assert controller._driver._driver is fake_driver


def test_connect_delegates_to_driver(controller, inputs):
    controller.connect()
    assert inputs() == [("connect",)]


def test_close_delegates_to_driver(controller, inputs):
    controller.close()
    assert inputs() == [("close",)]


def test_close_releases_held_inputs(controller, inputs):
    controller.down(Key.SHIFT)
    controller.close()
    assert inputs() == [("key_down", Key.SHIFT), ("key_up", Key.SHIFT), ("close",)]


# --- environment checks ---


@pytest.fixture
def outdated_dataset(tmp_path, monkeypatch):
    """Runs the test from tmp_path, with a dataset 'app' that was never synced."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("guimauve.storage.sync.files", lambda _pkg: tmp_path / "pkg")
    DataWorkspace().create_dataset("app")


@pytest.fixture
def two_screens(fake_driver):
    """A 1920x1080 primary screen with a 1280x720 screen on its right."""
    fake_driver.screen_rects = [Screen(0, 0, 3200, 1080), Screen(0, 0, 1920, 1080), Screen(1920, 0, 1280, 720)]
    return fake_driver


def test_checks_are_off_by_default(make_controller, outdated_dataset, fake_driver):
    make_controller()  # must not raise
    assert fake_driver.calls == []  # and must not capture the screen


@pytest.mark.parametrize(
    "checks",
    [
        {"screen": {"scaling": 0}},
        {"screen": {"size": [0, 1080]}},
        {"screen": {"number": 2}},
        {"screen": []},
        {"screen": [{"size": [1920, 1080]}, {"scaling": 100}]},
        {"datasets": []},
        {"datasets": ["Bad"]},
    ],
)
def test_invalid_checks_raise_model_error(make_controller, checks):
    with pytest.raises(ModelError):
        make_controller(parameters={"checks": checks})


def test_failed_dataset_check_raises(make_controller, outdated_dataset):
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"datasets": True}})
    assert exc_info.value.failures[0].startswith("datasets: 'app'")


def test_single_screen_shorthand_checks_screen_1(make_controller):
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"screen": {"size": [1280, 720]}}})
    assert exc_info.value.failures == ["screen 1: size expected 1280x720, got 1920x1080"]


def test_matching_screen_size_passes(make_controller):
    make_controller(parameters={"checks": {"screen": {"size": [1920, 1080]}}})  # must not raise


def test_each_screen_is_checked(make_controller, two_screens):
    screens = [{"number": 1, "size": [1920, 1080]}, {"number": 2, "size": [1920, 1080]}]
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"screen": screens}})
    assert exc_info.value.failures == ["screen 2: size expected 1920x1080, got 1280x720"]


def test_matching_screens_pass(make_controller, two_screens):
    screens = [{"number": 1, "size": [1920, 1080]}, {"number": 2, "size": [1280, 720]}]
    make_controller(parameters={"checks": {"screen": screens}})  # must not raise


def test_missing_screen_is_a_failure(make_controller, two_screens):
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"screen": {"number": 3, "size": [1920, 1080]}}})
    assert exc_info.value.failures == ["screen 3: does not exist, 2 screens available"]


def test_every_failure_is_reported_together(make_controller, outdated_dataset, two_screens):
    screens = [{"number": 1, "size": [1280, 720]}, {"number": 3, "size": [1, 1]}]
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"datasets": True, "screen": screens}})
    assert [failure.split(":")[0] for failure in exc_info.value.failures] == ["datasets", "screen 1", "screen 3"]


@pytest.fixture
def vnc_parameters(monkeypatch, fake_driver):
    """VNC parameters; the fake remote screen is 1920x1080 and, as with VNC, cannot list screens."""
    monkeypatch.setitem(controller_module.DRIVERS, "vnc", lambda **_: fake_driver)
    return {"execution_mode": "vnc", "vnc": {"host": "pc", "display": 0}}


def test_vnc_screen_is_not_checked_at_init(make_controller, vnc_parameters):
    make_controller(parameters={**vnc_parameters, "checks": {"screen": {"size": [1280, 720]}}})  # not connected yet


def test_vnc_screen_is_checked_on_connect(make_controller, vnc_parameters):
    controller = make_controller(parameters={**vnc_parameters, "checks": {"screen": {"size": [1280, 720]}}})
    with pytest.raises(EnvironmentCheckError) as exc_info:
        controller.connect()
    assert exc_info.value.failures == ["screen 1: size expected 1280x720, got 1920x1080"]


def test_vnc_other_screens_are_skipped_with_warning(make_controller, vnc_parameters, caplog):
    controller = make_controller(parameters={**vnc_parameters, "checks": {"screen": {"number": 2, "size": [1, 1]}}})
    with caplog.at_level(logging.WARNING):
        controller.connect()  # must not raise
    assert "Screen check skipped for screen 2" in caplog.text
