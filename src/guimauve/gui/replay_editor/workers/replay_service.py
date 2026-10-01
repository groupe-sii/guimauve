"""Wraps :class:`guimauve.recorder.Player` so replay runs off the UI thread."""

import threading

from PySide6.QtCore import QObject, Signal

from guimauve.drivers.local.driver import LocalDriver
from guimauve.models.input_event import InputEvent
from guimauve.recorder.player import Player


class ReplayService(QObject):
    """Runs ``Player.start(events)`` in a daemon thread.

    ``Player.start()`` sleeps between events to preserve timings, so
    calling it on the UI thread would freeze the window. This service
    emits :data:`finished` on the main thread once the replay is done.

    :cvar finished: Emitted from the main thread when the replay ends.
    """

    finished = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        """
        :param parent: Optional Qt parent.
        """
        super().__init__(parent)

    def start(self, events: list[InputEvent]) -> None:
        """Kick off a replay of ``events`` on a background thread.

        :param events: The events to replay, in order. An empty list
            still triggers :data:`finished`, but does nothing on screen.
        """

        def _run() -> None:
            Player(LocalDriver()).start(events)
            self.finished.emit()

        threading.Thread(target=_run, daemon=True).start()
