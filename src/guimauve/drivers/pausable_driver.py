import logging
import time
from contextlib import contextmanager
from threading import Lock
from typing import TYPE_CHECKING, Iterator, Optional

import numpy

from guimauve.drivers.driver import Driver
from guimauve.enums import Button, Key
from guimauve.models.area import Area

if TYPE_CHECKING:
    from guimauve.pause_manager import PauseManager

logger = logging.getLogger(__name__)


class PausableDriver(Driver):
    """Wraps a driver to release held inputs whenever control is given back to the user.

    Two situations suspend the driver:
    - pause: requested by the user through the pause manager, applied on the next driver call;
    - explicit suspension: requested by the caller (e.g. while an editor is open), applied immediately.

    On suspension, held keys and buttons are released and the mouse position is saved.
    On resume, the mouse is moved back to that position and held inputs are pressed again.
    Nested suspensions only release and restore once.
    """

    def __init__(self, driver: Driver, pause_manager: "PauseManager"):
        self._driver = driver
        self._pause_manager = pause_manager
        self._held_keys: list[Key] = []
        self._held_buttons: list[Button] = []
        self._last_position: Optional[tuple[int, int]] = None
        self._saved_position: Optional[tuple[int, int]] = None
        self._suspend_depth = 0
        self._explicit_suspend_depth = 0
        self._suspend_start = 0.0
        self._suspended_time = 0.0
        self._state_lock = Lock()
        self._pause_lock = Lock()

    @property
    def suspended_time(self) -> float:
        """Total time, in seconds, spent suspended."""
        return self._suspended_time

    @contextmanager
    def suspended(self) -> Iterator[None]:
        """Releases held inputs for the duration of the block. Pause checks are skipped meanwhile."""
        with self._state_lock:
            self._explicit_suspend_depth += 1
        self._suspend()
        try:
            yield
        finally:
            self._resume()
            with self._state_lock:
                self._explicit_suspend_depth -= 1

    def capture(self, area: Optional[Area] = None) -> numpy.ndarray:
        self._wait_if_paused()
        return self._driver.capture(area)

    def key_down(self, key: Key):
        self._wait_if_paused()
        self._driver.key_down(key)
        if key not in self._held_keys:
            self._held_keys.append(key)

    def key_up(self, key: Key):
        self._wait_if_paused()
        self._driver.key_up(key)
        if key in self._held_keys:
            self._held_keys.remove(key)

    def mouse_down(self, button: Button):
        self._wait_if_paused()
        self._driver.mouse_down(button)
        if button not in self._held_buttons:
            self._held_buttons.append(button)

    def mouse_up(self, button: Button):
        self._wait_if_paused()
        self._driver.mouse_up(button)
        if button in self._held_buttons:
            self._held_buttons.remove(button)

    def mouse_move(self, x: int, y: int):
        self._wait_if_paused()
        self._driver.mouse_move(x, y)
        self._last_position = (x, y)

    def mouse_scroll(self, v: int, h: int):
        self._wait_if_paused()
        self._driver.mouse_scroll(v, h)

    def mouse_position(self) -> tuple[int, int]:
        return self._driver.mouse_position()

    def paste(self, text: str):
        self._wait_if_paused()
        self._driver.paste(text)

    def type(self, text: str):
        self._wait_if_paused()
        self._driver.type(text)

    def connect(self):
        self._driver.connect()

    def close(self):
        try:
            self._release_held()
            self._held_keys.clear()
            self._held_buttons.clear()
        finally:
            self._driver.close()

    def _wait_if_paused(self) -> None:
        if self._explicit_suspend_depth or not self._pause_manager.is_paused():
            return

        # Only the first thread handles the pause, the others wait on the lock until inputs are restored.
        with self._pause_lock:
            if not self._pause_manager.is_paused():
                return

            self._suspend()
            try:
                self._pause_manager.wait_while_paused()
            finally:
                self._resume()

    def _suspend(self) -> None:
        with self._state_lock:
            self._suspend_depth += 1
            if self._suspend_depth > 1:
                return

            self._suspend_start = time.monotonic()
            self._saved_position = self._last_position or self._driver.mouse_position()
            self._release_held()
            logger.info("Driver suspended")

    def _resume(self) -> None:
        with self._state_lock:
            self._suspend_depth -= 1
            if self._suspend_depth > 0:
                return

            # Restore position before pressing again, to avoid clicking or dragging elsewhere.
            if self._saved_position:
                self._driver.mouse_move(*self._saved_position)
            self._press_held()
            self._suspended_time += time.monotonic() - self._suspend_start
            logger.info("Driver resumed")

    def _release_held(self) -> None:
        # Calls the wrapped driver directly: no pause check, held state is kept for restore.
        for button in reversed(self._held_buttons):
            self._driver.mouse_up(button)
        for key in reversed(self._held_keys):
            self._driver.key_up(key)

    def _press_held(self) -> None:
        for key in self._held_keys:
            self._driver.key_down(key)
        for button in self._held_buttons:
            self._driver.mouse_down(button)
