import json

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


def test_checks_are_off_by_default(make_controller, outdated_dataset, fake_driver):
    make_controller()  # must not raise
    assert fake_driver.calls == []  # and must not capture the screen


@pytest.mark.parametrize(
    "checks", [{"scaling": 0}, {"screen_size": [0, 1080]}, {"datasets": []}, {"datasets": ["Bad"]}]
)
def test_invalid_checks_raise_model_error(make_controller, checks):
    with pytest.raises(ModelError):
        make_controller(parameters={"checks": checks})


def test_failed_dataset_check_raises(make_controller, outdated_dataset):
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"datasets": True}})
    assert exc_info.value.failures[0].startswith("datasets: 'app'")


def test_screen_size_is_checked_at_init_in_local_mode(make_controller):
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"screen_size": [1280, 720]}})
    assert exc_info.value.failures == ["screen_size: expected 1280x720, got 1920x1080"]


def test_matching_screen_size_passes(make_controller):
    make_controller(parameters={"checks": {"screen_size": [1920, 1080]}})  # must not raise


def test_every_failure_is_reported_together(make_controller, outdated_dataset):
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"datasets": True, "screen_size": [1280, 720]}})
    assert [failure.split(":")[0] for failure in exc_info.value.failures] == ["datasets", "screen_size"]


def test_screen_size_checks_the_default_screen(make_controller, fake_driver):
    fake_driver.screen_rects = [Screen(0, 0, 3200, 1080), Screen(0, 0, 1920, 1080), Screen(1920, 0, 1280, 720)]
    parameters = {"default": {"screen": 2, "timeout": 5}, "checks": {"screen_size": [1280, 720]}}
    make_controller(parameters=parameters)  # must not raise: screen 2 is 1280x720


@pytest.fixture
def vnc_parameters(monkeypatch, fake_driver):
    """VNC parameters expecting a 1280x720 screen, while the fake remote screen is 1920x1080."""
    monkeypatch.setitem(controller_module.DRIVERS, "vnc", lambda **_: fake_driver)
    return {
        "execution_mode": "vnc",
        "vnc": {"host": "pc", "display": 0},
        "checks": {"screen_size": [1280, 720]},
    }


def test_vnc_screen_is_not_checked_at_init(make_controller, vnc_parameters):
    make_controller(parameters=vnc_parameters)  # must not raise: not connected yet


def test_vnc_screen_is_checked_on_connect(make_controller, vnc_parameters):
    controller = make_controller(parameters=vnc_parameters)
    with pytest.raises(EnvironmentCheckError) as exc_info:
        controller.connect()
    assert exc_info.value.failures == ["screen_size: expected 1280x720, got 1920x1080"]
