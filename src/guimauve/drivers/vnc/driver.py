import os
import tempfile
from functools import wraps
from threading import Lock

import cv2 as cv
from twisted.internet import reactor as _reactor
from vncdotool import api, client

from guimauve.drivers.driver import Driver
from guimauve.drivers.vnc.bindings import KEY_MAP, MOUSE_MAP


def handle_key(func):
    @wraps(func)
    def wrapper(self, key):
        if key not in KEY_MAP:
            raise ValueError(f"Key {key} is not supported in VNC mode")
        func(self, KEY_MAP[key])

    return wrapper


class VNCDriver(Driver):
    _active_clients = set()
    _lock = Lock()

    def __init__(self, host, display, port, password):
        self.host = host
        self.display = display
        self.port = port
        self.password = password
        self._client = None
        self._mouse_position = 0, 0

    def capture(self, area=None):
        file_ = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file_.close()

        if area is None:
            self._client.captureScreen(file_.name)
        else:
            self._client.captureRegion(file_.name, area.left, area.top, area.width, area.height)

        raw_img = cv.imread(file_.name)
        img = cv.cvtColor(raw_img, cv.COLOR_BGR2RGB)
        os.unlink(file_.name)

        return img

    @handle_key
    def key_down(self, key):
        self._client.keyDown(key)

    @handle_key
    def key_up(self, key):
        self._client.keyUp(key)

    def mouse_down(self, button):
        self._client.mouseDown(MOUSE_MAP[button])

    def mouse_up(self, button):
        self._client.mouseUp(MOUSE_MAP[button])

    def mouse_move(self, x, y):
        self._client.mouseMove(x, y)
        self._mouse_position = x, y

    def mouse_scroll(self, v, h):
        if v > 0:
            for _ in range(v):
                self._client.mousePress(4)
        elif v < 0:
            for _ in range(abs(v)):
                self._client.mousePress(5)
        if h > 0:
            for _ in range(h):
                self._client.mousePress(7)
        elif h < 0:
            for _ in range(abs(h)):
                self._client.mousePress(6)

    def mouse_position(self):
        return self._mouse_position

    def paste(self, text):
        self._client.paste(text)
        self._client.keyDown("ctrl")
        self._client.keyPress("v")
        self._client.keyUp("ctrl")

    def type(self, text):
        for char in text:
            self._client.keyPress(char)

    def connect(self):
        server = f"{self.host}:{self.display or ''}"
        if self.port:
            server = f"{server}:{self.port}"

        factory = client.VNCDoToolFactory
        factory.nocursor = True

        self._client = api.connect(server, factory_class=factory, password=self.password)

        with VNCDriver._lock:
            VNCDriver._active_clients.add(self._client)

    def close(self):
        if self._client is None:
            return

        self._client.disconnect()

        with VNCDriver._lock:
            VNCDriver._active_clients.discard(self._client)
            if not VNCDriver._active_clients:
                VNCDriver._shutdown()

        self._client = None

    @staticmethod
    def _shutdown():
        if not _reactor.running:
            return
        _reactor.callFromThread(_reactor.crash)
        if api._THREAD is not None:
            api._THREAD.join(timeout=5.0)
            api._THREAD = None

        if _reactor.threadpool is not None:
            _reactor.threadpool.stop()
            _reactor.threadpool = None
