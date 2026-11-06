"""Logging of guimauve: the helper to show the logs, and the conventions the modules follow.

Guimauve logs through the standard ``logging`` module, one logger per module under the ``guimauve`` logger. Nothing is
shown until the application configures logging, with :func:`setup_logging` or as it would for any library.

Levels:

- INFO: what the user calls directly (actions of the controller, CLI commands, editor opened and closed).
- DEBUG: the details (detection, driver inputs, files written).
- WARNING: a degraded mode (a check skipped, a screen ignored).
"""

import json as json_
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = "guimauve"
FIELDS = "guimauve"
"""Attribute of the log record holding the structured fields, see :func:`fields`."""

_SPECIALS = "/", "\\", ".", "?", "*"
_TEXT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

_handler: logging.Handler | None = None
_levels: list[str] = []


def fields(**values: Any) -> dict[str, dict[str, Any]]:
    """Gives the structured fields of a log, to pass as the ``extra`` argument of the log call.

    The fields are kept under a single attribute of the record, so they never clash with the attributes of
    ``logging.LogRecord``. Fields set to None are dropped.

    Example: ``logger.info("click on %s", name, extra=fields(action="click", element=name))``

    :param values: The fields of the log.
    :return: The ``extra`` argument of the log call.
    """
    return {FIELDS: {key: value for key, value in values.items() if value is not None}}


def mask(text: str) -> str:
    """Hides a text typed on the keyboard, which may be a password: only its first character is kept.

    :param text: Text typed.
    :return: The text without the characters that are special in a file name, cut to ``first character + xxx`` when it
        has 2 characters or more.
    """
    for special in _SPECIALS:
        text = text.replace(special, "")
    return f"{text[0]}xxx" if len(text) >= 2 else text


class JsonFormatter(logging.Formatter):
    """Formats a log as a JSON object on a single line, its structured fields as keys."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        entry.update(getattr(record, FIELDS, None) or {})
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json_.dumps(entry, default=str, ensure_ascii=False)


def setup_logging(
    level: int | str = "INFO",
    *,
    levels: dict[str, int | str] | None = None,
    json: bool = False,
    file: Path | str | None = None,
) -> logging.Handler:
    """Shows the logs of guimauve, on stderr or in a file.

    Only the ``guimauve`` logger is configured: the logs of the other libraries are left as they are. Calling it again
    replaces what the previous call set.

    Example: ``setup_logging("WARNING", levels={"controller": "INFO", "drivers": "DEBUG"})``

    :param level: Level of the logs shown, for every part not given in ``levels``.
    :param levels: Level of a part of guimauve, by name: a short one (``"controller"``, ``"drivers"``,
        ``"detection"``...) or a full logger name (``"guimauve.detection.ocr"``).
    :param json: True to write a JSON object per line, else a line of text.
    :param file: File to append the logs to; None writes them on stderr.
    :return: The handler added, to remove it later if needed.
    """
    global _handler

    root = logging.getLogger(ROOT)
    if _handler is not None:
        root.removeHandler(_handler)
        _handler.close()
    for name in _levels:
        logging.getLogger(name).setLevel(logging.NOTSET)
    _levels.clear()

    handler: logging.Handler = (
        logging.FileHandler(file, encoding="utf-8") if file is not None else logging.StreamHandler(sys.stderr)
    )
    # The levels of the loggers filter the logs: a handler level would block a part set to a lower level.
    # The message holds the fields in words: the text format leaves them out, the JSON one writes them as keys.
    handler.setFormatter(JsonFormatter() if json else logging.Formatter(_TEXT_FORMAT))
    root.addHandler(handler)
    root.setLevel(_level(level))

    for name, part_level in (levels or {}).items():
        full_name = logger_name(name)
        logging.getLogger(full_name).setLevel(_level(part_level))
        _levels.append(full_name)

    _handler = handler
    return handler


def logger_name(name: str) -> str:
    """Gives the full name of the logger of a part of guimauve.

    :param name: A short name (``"drivers"``) or a full one (``"guimauve.drivers"``).
    :return: The full logger name.
    """
    return name if name == ROOT or name.startswith(f"{ROOT}.") else f"{ROOT}.{name}"


def _level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    value = logging.getLevelName(level.upper())
    if not isinstance(value, int):
        raise ValueError(f"Unknown log level {level!r}")
    return value
