import logging

import pytest

from guimauve.detection.detector import Match, Point
from guimauve.enums import Key
from guimauve.models.element import Element
from guimauve.models.variant import ImageVariant


@pytest.fixture
def logs(caplog):
    """Records every log of guimauve, DEBUG included."""
    caplog.set_level(logging.DEBUG, logger="guimauve")
    return caplog


def image(path, name="BUTTON") -> Element:
    return Element(name=name, timeout=0.05, variants=[ImageVariant(name="DEFAULT", path=path)])


def actions(caplog, level=None) -> list[logging.LogRecord]:
    """Logs of the actions of the controller, at a level or all of them."""
    return [
        record
        for record in caplog.records
        if record.name == "guimauve.controller"
        and "action" in getattr(record, "guimauve", {})
        and (level is None or record.levelno == level)
    ]


def test_init_logs_the_mode(make_controller, logs):
    make_controller()
    assert "Controller ready: local mode" in logs.messages


def test_vnc_password_is_never_logged(make_controller, fake_driver, monkeypatch, logs):
    import guimauve.controller as controller_module

    monkeypatch.setitem(controller_module.DRIVERS, "vnc", lambda **_: fake_driver)
    make_controller(parameters={"execution_mode": "vnc", "vnc": {"host": "pc", "display": 0, "password": "s3cr3t"}})

    assert "s3cr3t" not in logs.text
    assert "***" in logs.text


def test_click_on_element_logs_how_it_was_found(controller, detectors, needle_path, fake_driver, logs):
    detectors["template"].matches = [Match(box=None, target=Point(40, 30), confidence=0.97)]

    controller.click(on=image(needle_path))

    [record] = actions(logs, logging.INFO)
    message = record.getMessage()
    assert message.startswith("click on BUTTON at (40, 30) [template, variant DEFAULT, screen 1, confidence 0.97]")
    assert record.guimauve["method"] == "template"
    assert record.guimauve["variant"] == "DEFAULT"
    assert record.guimauve["target"] == [40, 30]
    assert record.guimauve["success"] is True


def test_locate_not_found(controller, detectors, needle_path, logs):
    controller.locate(element=image(needle_path))

    [record] = actions(logs, logging.INFO)
    assert record.getMessage().startswith("locate BUTTON: not found")
    assert record.guimauve["success"] is False


def test_wait_logs_each_element(controller, detectors, needle_path, logs):
    detectors["template"].matches = [Match(box=None, target=Point(1, 2), confidence=1.0)]

    controller.wait(on=image(needle_path))

    [record] = actions(logs, logging.INFO)
    assert record.getMessage().startswith("wait on BUTTON (found in ")
    assert ": success" in record.getMessage()
    assert any("BUTTON found after 1 search(es)" in message for message in logs.messages)


def test_nested_actions_are_logged_at_debug(controller, detectors, needle_path, logs):
    detectors["template"].matches = [Match(box=None, target=Point(1, 2), confidence=1.0)]

    controller.scroll_until(v=-1, element=image(needle_path))

    assert [record.guimauve["action"] for record in actions(logs, logging.INFO)] == ["scroll_until"]
    assert [record.guimauve["action"] for record in actions(logs, logging.DEBUG)] == ["locate"]


def test_typed_text_is_masked(controller, logs):
    controller.type("password123")
    controller.type("password123", interval=0.01)

    assert "password123" not in logs.text
    assert "assword" not in logs.text
    assert [record.getMessage().split(" in ")[0] for record in actions(logs, logging.INFO)] == [
        "type 'pxxx'",
        "type 'pxxx'",
    ]


def test_press_logs_the_keys(controller, logs):
    controller.press(Key.CTRL, Key.C)

    [record] = actions(logs, logging.INFO)
    assert record.getMessage().startswith("press CTRL+C")


def test_driver_inputs_are_logged_at_debug(controller, logs):
    controller.press(Key.ENTER)

    driver = [r.getMessage() for r in logs.records if r.name == "guimauve.drivers"]
    assert driver == ["key down ENTER", "key up ENTER"]
    assert all(r.levelno == logging.DEBUG for r in logs.records if r.name == "guimauve.drivers")


def test_typing_one_by_one_is_logged_once(controller, logs):
    controller.type("password123", interval=0.01)

    driver = [r.getMessage() for r in logs.records if r.name == "guimauve.drivers"]
    assert driver == ["type 11 character(s) one by one"]


def test_fixed_position_is_logged_once(controller, logs):
    controller.double_click(on=Element(name="CORNER", x=10, y=20))

    fixed = [r.getMessage() for r in logs.records if r.name == "guimauve.detection.locate"]
    assert fixed == ["CORNER: fixed position (10, 20)"]


def test_element_found_is_not_logged_as_a_fixed_position(controller, detectors, needle_path, logs):
    detectors["template"].matches = [Match(box=None, target=Point(40, 30), confidence=1.0)]

    controller.click(on=image(needle_path))

    assert not any("fixed position" in message for message in logs.messages)


def test_detection_details_at_debug(controller, detectors, needle_path, logs):
    detectors["template"].matches = [Match(box=None, target=Point(1, 2), confidence=0.91)]

    controller.locate(element=image(needle_path))

    [record] = [r for r in logs.records if r.name == "guimauve.detection.locate" and "status" in r.guimauve]
    assert record.levelno == logging.DEBUG
    assert record.getMessage().startswith("variant DEFAULT on screen 1: 1 match(es) by template, best confidence 0.91")


def test_nothing_is_computed_for_the_logs_when_disabled(controller, fake_driver, caplog):
    caplog.set_level(logging.WARNING, logger="guimauve")

    controller.click()

    # mouse_position is read once by the screenshot logging step, not by the action log
    assert [call[0] for call in fake_driver.calls].count("mouse_position") == 1
