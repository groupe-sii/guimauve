import logging
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Lock
from typing import TYPE_CHECKING

import numpy

from guimauve.drivers.driver import Driver, Screen
from guimauve.enums import Button, Key
from guimauve.log import fields
from guimauve.models.area import Area

if TYPE_CHECKING:
    from guimauve.pause_manager import PauseManager

# Named after the drivers rather than this module: the users see "driver", the pausable wrapper is a detail
logger = logging.getLogger("guimauve.drivers")


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
        self._last_position: tuple[int, int] | None = None
        self._saved_position: tuple[int, int] | None = None
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

    def capture(self, screen: int, area: Area | None = None) -> numpy.ndarray:
        self._wait_if_paused()
        logger.debug("capture screen %s", screen, extra=fields(input="capture", screen=screen))
        return self._driver.capture(screen, area)

    def screens(self) -> list[Screen]:
        return self._driver.screens()

    def key_down(self, key: Key):
        self._wait_if_paused()
        logger.debug("key down %s", key.name, extra=fields(input="key_down", key=key.name))
        self._driver.key_down(key)
        if key not in self._held_keys:
            self._held_keys.append(key)

    def key_up(self, key: Key):
        self._wait_if_paused()
        logger.debug("key up %s", key.name, extra=fields(input="key_up", key=key.name))
        self._driver.key_up(key)
        if key in self._held_keys:
            self._held_keys.remove(key)

    def mouse_down(self, button: Button):
        self._wait_if_paused()
        logger.debug("mouse down %s", button.name, extra=fields(input="mouse_down", button=button.name))
        self._driver.mouse_down(button)
        if button not in self._held_buttons:
            self._held_buttons.append(button)

    def mouse_up(self, button: Button):
        self._wait_if_paused()
        logger.debug("mouse up %s", button.name, extra=fields(input="mouse_up", button=button.name))
        self._driver.mouse_up(button)
        if button in self._held_buttons:
            self._held_buttons.remove(button)

    def mouse_move(self, x: int, y: int):
        # Not logged: a smooth move makes up to 100 of them, the action logs where the mouse ends
        self._wait_if_paused()
        self._driver.mouse_move(x, y)
        self._last_position = (x, y)

    def mouse_scroll(self, v: int, h: int):
        self._wait_if_paused()
        logger.debug("mouse scroll v=%d h=%d", v, h, extra=fields(input="mouse_scroll", v=v, h=h))
        self._driver.mouse_scroll(v, h)

    def mouse_position(self) -> tuple[int, int]:
        return self._driver.mouse_position()

    def paste(self, text: str):
        self._wait_if_paused()
        # Never the text itself: it may be a password
        logger.debug("paste %d characters", len(text), extra=fields(input="paste", chars=len(text)))
        self._driver.paste(text)

    def type(self, text: str):
        self._wait_if_paused()
        # Never the text itself: typed one character at a time, it would show a password in full
        logger.debug("type %d character(s)", len(text), extra=fields(input="type", chars=len(text)))
        self._driver.type(text)

    def type_one_by_one(self, text: str, between: Callable[[], None]) -> None:
        """Types a text one character at a time, logged once rather than once per character.

        :param text: Text to type.
        :param between: Called after each character, to wait before the next one.
        """
        # Never the text itself: it may be a password
        logger.debug(
            "type %d character(s) one by one", len(text), extra=fields(input="type", chars=len(text), one_by_one=True)
        )
        for char in text:
            self._wait_if_paused()
            self._driver.type(char)
            between()

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

            self._suspend_start = time.perf_counter()
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
            self._suspended_time += time.perf_counter() - self._suspend_start
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
