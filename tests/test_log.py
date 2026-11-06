import json
import logging
import sys

import pytest

import guimauve
from guimauve import log
from guimauve.log import JsonFormatter, fields, mask, setup_logging


@pytest.fixture(autouse=True)
def reset_logging():
    """Undoes what setup_logging set, so that each test starts as an application that configured nothing."""
    yield
    root = logging.getLogger("guimauve")
    if log._handler is not None:
        root.removeHandler(log._handler)
        log._handler.close()
        log._handler = None
    for name in log._levels:
        logging.getLogger(name).setLevel(logging.NOTSET)
    log._levels.clear()
    root.setLevel(logging.NOTSET)


def lines(path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_nothing_is_shown_by_default():
    assert any(isinstance(handler, logging.NullHandler) for handler in logging.getLogger("guimauve").handlers)


def test_setup_logging_is_exported():
    assert guimauve.setup_logging is setup_logging


def test_setup_logging_shows_the_level_asked(tmp_path):
    file = tmp_path / "run.log"
    setup_logging("INFO", file=file)

    logging.getLogger("guimauve.controller").info("shown")
    logging.getLogger("guimauve.controller").debug("hidden")

    [line] = lines(file)
    assert line.endswith("INFO    guimauve.controller: shown")


def test_setup_logging_twice_replaces_the_handler(tmp_path):
    first, second = tmp_path / "first.log", tmp_path / "second.log"
    setup_logging("INFO", file=first)
    setup_logging("INFO", file=second)

    logging.getLogger("guimauve").info("once")

    assert lines(first) == []
    assert len(lines(second)) == 1
    assert len([h for h in logging.getLogger("guimauve").handlers if not isinstance(h, logging.NullHandler)]) == 1


def test_setup_logging_leaves_the_other_libraries(tmp_path):
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level

    setup_logging("DEBUG", file=tmp_path / "run.log")

    assert root.handlers == handlers
    assert root.level == level


@pytest.mark.parametrize("name", ["controller", "guimauve.controller"])
def test_levels_by_part(tmp_path, name):
    file = tmp_path / "run.log"
    setup_logging("WARNING", levels={name: "INFO", "drivers": "DEBUG"}, file=file)

    logging.getLogger("guimauve.controller").info("controller info")
    logging.getLogger("guimauve.controller").debug("controller debug")
    logging.getLogger("guimauve.drivers.vnc.driver").debug("driver debug")
    logging.getLogger("guimauve.detection.locate").info("detection info")
    logging.getLogger("guimauve.detection.locate").warning("detection warning")

    messages = [line.split(": ", 1)[1] for line in lines(file)]
    assert messages == ["controller info", "driver debug", "detection warning"]


def test_setup_logging_again_resets_the_levels_by_part(tmp_path):
    setup_logging("WARNING", levels={"drivers": "DEBUG"}, file=tmp_path / "first.log")
    setup_logging("WARNING", file=tmp_path / "second.log")

    assert logging.getLogger("guimauve.drivers").level == logging.NOTSET


def test_unknown_level_is_refused():
    with pytest.raises(ValueError, match="Unknown log level"):
        setup_logging("LOUD")


def test_json_lines_hold_the_fields(tmp_path):
    file = tmp_path / "run.jsonl"
    setup_logging("INFO", json=True, file=file)

    logging.getLogger("guimauve.controller").info(
        "click on %s", "OK", extra=fields(action="click", element="OK", target=[1, 2], screen=None)
    )

    [entry] = [json.loads(line) for line in lines(file)]
    assert entry["level"] == "INFO"
    assert entry["logger"] == "guimauve.controller"
    assert entry["msg"] == "click on OK"
    assert entry["action"] == "click"
    assert entry["target"] == [1, 2]
    assert "screen" not in entry  # None fields are dropped
    assert "ts" in entry


def test_json_formatter_writes_the_exception():
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logging.getLogger("guimauve").makeRecord(
            "guimauve", logging.ERROR, __file__, 1, "failed", (), exc_info=sys.exc_info()
        )
    assert "RuntimeError: boom" in json.loads(JsonFormatter().format(record))["exc"]


@pytest.mark.parametrize(
    ("text", "masked"),
    [("password", "pxxx"), ("a", "a"), ("", ""), ("C:\\dir/file.txt", "Cxxx")],
)
def test_mask_keeps_only_the_first_character(text, masked):
    assert mask(text) == masked
