"""Captures of the screens for the editor: at opening, now, or after a countdown."""

from collections.abc import Callable, Sequence

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QWidget

from guimauve.gui.element_editor_next.system import ScreenMap, out_of_capture

Captures = dict[int, np.ndarray]
"""Capture of each screen of the driver, by number."""
TICK_MS = 1000


class CaptureService(QObject):
    """Takes a capture of every screen of the driver, one by one, keeping the windows of the editor out of them.

    The captures at opening are taken before the editor shows; the others inside out_of_capture. A countdown runs
    on a timer, the interface staying usable, and the windows leave the captures only once it ends. The signals
    carry no data: the captures, the seconds left and the error are read from the service.

    :param provider: Captures a screen by its number, as Driver.capture.
    :param screens: Screens of the driver.
    :param tick_ms: Length of a second of the countdown, shorter in the tests.
    """

    countdown_changed = Signal()
    """A countdown started, went down by a second, ended or was cancelled."""
    captured = Signal()
    failed = Signal()
    """The driver could not capture a screen; see error."""

    def __init__(
        self,
        provider: Callable[[int], np.ndarray],
        screens: ScreenMap,
        parent: QObject | None = None,
        tick_ms: int = TICK_MS,
    ):
        super().__init__(parent)
        self._provider = provider
        self._screens = screens
        self._windows: Sequence[QWidget] = ()
        self._initial: Captures = {}
        self._last: Captures = {}
        self._error: str | None = None
        self._remaining: int | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(tick_ms)
        self._timer.timeout.connect(self._tick)

    @property
    def screens(self) -> ScreenMap:
        return self._screens

    def set_windows(self, windows: Sequence[QWidget]) -> None:
        """Windows of the editor to keep out of the captures taken from now on."""
        self._windows = list(windows)

    # Captures

    def take_initial(self) -> bool:
        """Takes the captures at opening, before any window of the editor shows; False when the driver fails."""
        captures = self._grab()
        self._initial = captures or {}
        return captures is not None

    def initial(self) -> Captures:
        return dict(self._initial)

    def last(self) -> Captures:
        """Captures of the last capture_now or countdown that succeeded."""
        return dict(self._last)

    @property
    def error(self) -> str | None:
        """Message of the last failure of the driver."""
        return self._error

    def capture_now(self) -> None:
        """Captures every screen, then emits captured, or failed."""
        self.cancel()
        with out_of_capture(self._windows):
            captures = self._grab()
        if captures is None:
            self.failed.emit()
        else:
            self._last = captures
            self.captured.emit()

    # Countdown

    @property
    def remaining(self) -> int | None:
        """Seconds left before the capture, None without countdown."""
        return self._remaining

    def capture_later(self, seconds: int) -> None:
        """Starts a countdown of some seconds, then captures as capture_now; a countdown already running restarts."""
        self._timer.stop()
        if seconds <= 0:
            self._remaining = None
            self.capture_now()
            return
        self._remaining = seconds
        self._timer.start()
        self.countdown_changed.emit()

    def cancel(self) -> None:
        """Stops the countdown, without capturing."""
        if self._remaining is not None:
            self._timer.stop()
            self._remaining = None
            self.countdown_changed.emit()

    def _tick(self) -> None:
        assert self._remaining is not None
        self._remaining -= 1
        if self._remaining > 0:
            self.countdown_changed.emit()
            return
        self._timer.stop()
        self._remaining = None
        self.countdown_changed.emit()
        self.capture_now()

    def _grab(self) -> Captures | None:
        try:
            captures = {number: self._provider(number) for number in self._screens.numbers()}
        except Exception as error:  # noqa: BLE001 - any failure of the driver is reported to the user
            self._error = str(error) or type(error).__name__
            return None
        self._error = None
        return captures
