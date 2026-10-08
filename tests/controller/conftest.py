import pytest

import guimauve.controller as controller_module
from guimauve.controller import Controller

# Calls issued by the controller itself (bookkeeping, logging) rather than by the action under test.
_NOISE = {"mouse_position", "capture"}


@pytest.fixture
def sleeps(monkeypatch):
    """Records every delay passed to the controller's sleep instead of waiting."""
    recorded: list[float] = []
    monkeypatch.setattr(controller_module, "sleep_", recorded.append)
    return recorded


@pytest.fixture
def make_controller(monkeypatch, fake_driver, fake_listener_cls, sleeps):
    """Builds a Controller wired to the fake driver, without any real pynput listener."""
    monkeypatch.setattr("guimauve.pause_manager.Listener", fake_listener_cls)
    monkeypatch.setitem(controller_module.DRIVERS, "local", lambda **_: fake_driver)

    def factory(*, parameters=None) -> Controller:
        return Controller(parameters=parameters)

    return factory


@pytest.fixture
def controller(make_controller):
    return make_controller()


@pytest.fixture
def inputs(fake_driver):
    """Returns the driver calls that reach the system, without the controller's bookkeeping."""

    def filtered() -> list[tuple]:
        return [call for call in fake_driver.calls if call[0] not in _NOISE]

    return filtered


@pytest.fixture
def ocr(ocr, monkeypatch):
    """Also replaces the Ocr class the controller uses directly, for read_text and locate_text."""
    monkeypatch.setattr(controller_module, "Ocr", ocr)
    return ocr
