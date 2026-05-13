from functools import wraps

import cv2 as cv
import numpy as np
import pynput
import pyperclip
from mss import mss

from guimauve.drivers.driver import Driver
from guimauve.drivers.local.bindings import KEY_MAP, MOUSE_MAP


def handle_key(func):
    @wraps(func)
    def wrapper(self, key):
        if key not in KEY_MAP:
            raise ValueError(f"Key {key} is not supported in local mode")
        func(self, KEY_MAP[key])

    return wrapper


class LocalDriver(Driver):
    """
    LocalDriver is a class that represents a local driver for the guimauve framework.
    It is used to run tests locally on the machine where the code is executed.
    """

    def __init__(self):
        self._keyboard = pynput.keyboard.Controller()
        self._mouse = pynput.mouse.Controller()

    def capture(self, area=None):
        with mss() as sct:
            if area:
                monitor = {
                    "left": area.left,
                    "top": area.top,
                    "width": area.width,
                    "height": area.height,
                }
            else:
                for m in sct.monitors[1:]:
                    if m["left"] == 0 and m["top"] == 0:
                        monitor = m
                        break
                else:
                    raise ValueError("No monitor found")
            img = np.array(sct.grab(monitor))
            return cv.cvtColor(img, cv.COLOR_BGR2RGB)

    @handle_key
    def key_down(self, key):
        self._keyboard.press(key)

    @handle_key
    def key_up(self, key):
        self._keyboard.release(key)

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
