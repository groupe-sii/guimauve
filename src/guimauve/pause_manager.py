import logging
from threading import Event, Lock
from typing import TYPE_CHECKING

from guimauve.enums import Key

if TYPE_CHECKING:
    from pynput.keyboard import Key as Key_
    from pynput.keyboard import KeyCode

try:
    from pynput.keyboard import Listener

    from guimauve.drivers.local.bindings import KEY_MAP
except ImportError as e:  # no display to listen to, as on a Linux server driving a VNC session
    Listener = None
    _NO_KEYBOARD = str(e)

logger = logging.getLogger(__name__)


class PauseManager:
    def __init__(self, pause_shortcut: list[Key]):
        self._pressed_keys: set[Key_ | KeyCode] = set()
        self._pause_event = Event()
        self._pause_event.set()
        self._lock = Lock()

        if Listener is None:
            self._keyboard_listener = None
            logger.warning("Pause shortcut disabled: cannot listen to the keyboard (%s)", _NO_KEYBOARD)
            return

        self._pause_shortcut = {KEY_MAP[key] for key in pause_shortcut}
        self._keyboard_listener = Listener(on_press=self._on_key_press, on_release=self._on_key_release)
        self._keyboard_listener.start()
        logger.info(f"Initialized with shortcut: {pause_shortcut}")

    def pause(self):
        with self._lock:
            self._pause_event.clear()
            logger.info("Pause requested")

    def resume(self):
        with self._lock:
            self._pause_event.set()
            logger.info("Resume requested")

    def wait_while_paused(self):
        self._pause_event.wait()

    def is_paused(self):
        return not self._pause_event.is_set()

    def _on_key_press(self, key):
        if key in self._pressed_keys:
            return

        self._pressed_keys.add(key)

        if self._pause_shortcut <= self._pressed_keys:
            if not self.is_paused():
                self.pause()
            else:
                self.resume()

    def _on_key_release(self, key):
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)

    def __del__(self):
        if self._keyboard_listener and self._keyboard_listener.running:
            self._keyboard_listener.stop()
