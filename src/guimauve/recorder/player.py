import json
from pathlib import Path
from typing import Union

from guimauve.drivers.driver import Driver
from guimauve.models.input_event import InputEvent
from guimauve.utils.time import sleep


class Player:
    """Replay recorded keyboard and mouse events.

    Takes a list of :class:`InputEvent` objects — either loaded from a JSON
    file previously produced by a Recorder, or passed directly in memory —
    and dispatches each event to the provided driver while preserving the
    original timing between events.

    :param driver: Object exposing methods matching event action names
        (e.g. ``key_down``, ``mouse_move``). Each method is called with
        the event's arguments unpacked.

    :ivar _driver: Driver used to execute the events.
    :ivar _events: Events currently loaded.
    :vartype _events: list[InputEvent]
    """

    def __init__(self, driver: Driver):
        self._driver = driver
        self._events: list[InputEvent] = []

    def start(self, events: Union[list[InputEvent], Path]) -> None:
        """Replay events in order, preserving the original timing.

        Each event is dispatched via
        ``getattr(self._driver, event.action)(*event.args)``. The delay
        between two consecutive events matches the delta between their
        original timestamps.

        :param events: Either a :class:`Path` to a JSON file to load, or a
            list of :class:`InputEvent` instances already in memory.
        :raises TypeError: If ``events`` is neither a Path nor a list.
        """
        if isinstance(events, Path):
            self._load(events)
        elif isinstance(events, list):
            self._events = events
        else:
            raise TypeError(f"events must be a Path or a list, got {type(events).__name__}")

        if not self._events:
            return

        prev_t = self._events[0].t
        for event in self._events:
            delta = event.t - prev_t
            if delta > 0:
                sleep(delta)
            getattr(self._driver, event.action)(*event.args)
            prev_t = event.t

    def _load(self, path: Path) -> None:
        """Load and validate events from a JSON file.

        Each event is constructed from the file's data and then validated
        via :meth:`InputEvent.resolve`, which coerces string arguments into
        their corresponding enum members.

        :param path: Path to the JSON file to load.
        """
        with path.open("r") as f:
            data = json.load(f)
        self._events = []
        for d in data:
            event = InputEvent(**d)
            event.resolve()
            self._events.append(event)
