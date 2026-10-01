"""Wraps :class:`guimauve.recorder.Recorder` in a Qt-friendly async API.

The main window creates one instance, calls :meth:`RecordingService.start`
when the toolbar's Record is toggled on, and listens for the
:data:`~RecordingService.stopped` signal instead of blocking on
``Recorder.wait()``.
"""

import threading

from PySide6.QtCore import QObject, Signal

from guimauve.enums import Key
from guimauve.models.input_event import InputEvent
from guimauve.recorder.recorder import Recorder


class RecordingService(QObject):
    """Runs a Recorder session in a background thread.

    The recorder itself uses pynput listeners that already run off the
    main thread, but ``Recorder.wait()`` blocks — so we call it from a
    daemon thread and re-emit its end as a Qt signal, safe to connect
    to any UI slot.

    :cvar stopped: Emitted from the main thread when the recording
        session ends.
    """

    stopped = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        """
        :param parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._recorder: Recorder | None = None

    @property
    def events(self) -> list[InputEvent]:
        """:return: Events captured during the last (or ongoing) session,
        or an empty list if no session has been started yet."""
        return self._recorder.events if self._recorder else []

    def start(self, stop_key: Key = Key.ESC) -> None:
        """Start a new recording session.

        :param stop_key: Key whose press ends the session and triggers
            the :data:`stopped` signal.
        """
        self._recorder = Recorder()
        self._recorder.start()

        def _wait_for_stop() -> None:
            self._recorder.wait(stop_key)
            self.stopped.emit()

        threading.Thread(target=_wait_for_stop, daemon=True).start()
