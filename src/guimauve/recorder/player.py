from guimauve.drivers.driver import Driver
from guimauve.models.input_event import InputEvent
from guimauve.utils.time import sleep


class Player:
    """Replay recorded keyboard and mouse events.

    Takes a list of :class:`InputEvent` objects already in memory and
    dispatches each event to the provided driver while preserving the
    original timing between events.

    :param driver: Object exposing methods matching event action names
        (e.g. ``key_down``, ``mouse_move``). Each method is called with
        the event's arguments unpacked.

    :ivar _driver: Driver used to execute the events.
    """

    def __init__(self, driver: Driver):
        self._driver = driver

    def start(self, events: list[InputEvent]) -> None:
        """Replay events in order, preserving the original timing.

        Each event is dispatched via
        ``getattr(self._driver, event.action)(*event.args)``. The delay
        between two consecutive events matches the delta between their
        original timestamps.

        :param events: List of :class:`InputEvent` instances to replay.
        """
        if not events:
            return

        prev_t = events[0].t
        for event in events:
            delta = event.t - prev_t
            if delta > 0:
                sleep(delta)
            getattr(self._driver, event.action)(*event.args)
            prev_t = event.t
