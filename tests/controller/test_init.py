import json

import pytest

from guimauve.checks import EnvironmentCheckError
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


def test_checks_are_off_by_default(make_controller, outdated_dataset):
    make_controller()  # must not raise


def test_failed_dataset_check_raises(make_controller, outdated_dataset):
    with pytest.raises(EnvironmentCheckError) as exc_info:
        make_controller(parameters={"checks": {"datasets": True}})
    assert [f.check for f in exc_info.value.failures] == ["datasets"]
