import logging
import sys
from functools import wraps

import cv2 as cv
import numpy as np
import pynput
import pyperclip
from mss import mss

from guimauve.drivers.driver import Driver, Screen
from guimauve.drivers.local.bindings import KEY_MAP, MOUSE_MAP
from guimauve.enums import Key

logger = logging.getLogger(__name__)

_NUM_LOCK_LED = 0x2
"""Bit of the Num Lock LED in the LED mask of X11."""

_NUM_LOCK_KEYS = {
    KEY_MAP[key]
    for key in (
        Key.KP_0,
        Key.KP_1,
        Key.KP_2,
        Key.KP_3,
        Key.KP_4,
        Key.KP_5,
        Key.KP_6,
        Key.KP_7,
        Key.KP_8,
        Key.KP_9,
        Key.KP_DECIMAL,
    )
}
"""Keypad keys that move the cursor instead of typing when Num Lock is off, under X11."""


def _num_lock_off() -> bool:
    """Whether Num Lock is off under X11; False elsewhere, where the keypad types its digits whatever its state."""
    if sys.platform != "linux":
        return False

    from Xlib.display import Display

    display = Display()
    try:
        return not display.get_keyboard_control().led_mask & _NUM_LOCK_LED
    finally:
        display.close()


def handle_key(func):
    @wraps(func)
    def wrapper(self, key):
        if key not in KEY_MAP:
            raise ValueError(f"Key {key} is not supported in local mode")
        func(self, KEY_MAP[key])

    return wrapper


def _number_screens(monitors: list[dict]) -> list[Screen]:
    """Numbers the monitors listed by mss.

    :param monitors: Monitors as listed by mss, the first one bounding all the others.
    :return: The screens by number: 0 bounds all of them, 1 is the one at the desktop origin (or the first listed by
        mss when no screen is there, possible on Linux with staggered screens), then the others from left to right and
        top to bottom.
    """
    bounding, *screens = (Screen(m["left"], m["top"], m["width"], m["height"]) for m in monitors)
    primary = next((i for i, s in enumerate(screens) if (s.left, s.top) == (0, 0)), 0)
    others = sorted(screens[:primary] + screens[primary + 1 :], key=lambda s: (s.left, s.top))
    return [bounding, screens[primary], *others]


class LocalDriver(Driver):
    """
    LocalDriver is a class that represents a local driver for the guimauve framework.
    It is used to run tests locally on the machine where the code is executed.
    """

    def __init__(self) -> None:
        self._keyboard = pynput.keyboard.Controller()
        self._mouse = pynput.mouse.Controller()
        # Keypad keys held down with Num Lock turned on for them, turned off again once all are released
        self._num_locked: set = set()

    def capture(self, screen, area=None):
        screens = self.screens()
        if not 0 <= screen < len(screens):
            raise ValueError(f"Screen {screen} does not exist: {len(screens) - 1} screens available")

        rect = screens[screen]
        if area and (area.right > rect.width or area.bottom > rect.height):
            raise ValueError(f"Area {area.as_ltrb()} exceeds the size of screen {screen}: {rect.width}x{rect.height}")

        left, top = rect.left + (area.left if area else 0), rect.top + (area.top if area else 0)
        width, height = (area.width, area.height) if area else (rect.width, rect.height)
        with mss() as sct:
            img = np.array(sct.grab({"left": left, "top": top, "width": width, "height": height}))

        return cv.cvtColor(img, cv.COLOR_BGR2RGB)

    def screens(self):
        with mss() as sct:
            return _number_screens(sct.monitors)

    @handle_key
    def key_down(self, key):
        # The keypad types its digits whatever the state of Num Lock, as on Windows
        if key in _NUM_LOCK_KEYS and (self._num_locked or _num_lock_off()):
            if not self._num_locked:
                logger.debug("Num Lock turned on to type on the keypad")
                self._toggle_num_lock()
            self._num_locked.add(key)
        self._keyboard.press(key)

    @handle_key
    def key_up(self, key):
        self._keyboard.release(key)
        if key in self._num_locked:
            self._num_locked.remove(key)
            if not self._num_locked:
                self._toggle_num_lock()

    def _toggle_num_lock(self):
        self._keyboard.press(pynput.keyboard.Key.num_lock)
        self._keyboard.release(pynput.keyboard.Key.num_lock)

    def mouse_down(self, button):
        self._mouse.press(MOUSE_MAP[button])

    def mouse_up(self, button):
        self._mouse.release(MOUSE_MAP[button])

    def mouse_move(self, x, y):
        self._mouse.position = x, y

    def mouse_scroll(self, v, h):
        self._mouse.scroll(h, v)

    def mouse_position(self):
        return self._mouse.position

    def paste(self, text):
        pyperclip.copy(text)
        with self._keyboard.pressed(pynput.keyboard.Key.ctrl):
            self._keyboard.press("v")
            self._keyboard.release("v")

    def type(self, text):
        self._keyboard.type(text)

    def connect(self):
        pass

    def close(self):
        pass
