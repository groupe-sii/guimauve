"""Process searching elements for another one, so that a long detection, such as the OCR, never holds its Python.

The other process starts it with ``python -m guimauve.detection.worker [module:function]``, writes a secret key on
its input, and reads on its output the port it listens to; then they talk through ``multiprocessing.connection``.

Requests, as tuples: ``("search", element, captures, screens, mouse_position)`` searches the element on the captures,
one at a time; ``("stop",)`` stops the search in progress at its next step; ``("quit",)`` ends the process. Answers:
``("report", report, seconds)`` or ``("error", message)``.
"""

import os
import queue
import sys
import threading
import time
from collections.abc import Callable
from importlib import import_module
from multiprocessing.connection import Connection, Listener
from typing import Any

import numpy as np

from guimauve.drivers.driver import Screen

Grab = Callable[[int], np.ndarray]
DEFAULT_LOCATE = "guimauve.detection.locate:locate_element"


def grabber(captures: dict[int, np.ndarray], screens: list[Screen]) -> Grab:
    """Gives the image of a screen from captures of each screen, as Driver.capture does.

    Screen 0 is made of the captures of the screens, at their place on the desktop, black between them. Without
    screens from the driver, as with VNC or a file, the only capture stands for any screen.

    :param captures: Capture of each screen, by number.
    :param screens: Screens of the driver; empty when unknown.
    """

    def grab(number: int) -> np.ndarray:
        if not screens:
            return next(iter(captures.values()))
        if number == 0:
            return _desktop(captures, screens)
        if number not in captures:
            raise ValueError(f"Screen {number} was not captured")
        return captures[number]

    return grab


def _desktop(captures: dict[int, np.ndarray], screens: list[Screen]) -> np.ndarray:
    bounds = screens[0]
    first = next(iter(captures.values()))
    desktop = np.zeros((bounds.height, bounds.width, *first.shape[2:]), first.dtype)
    for number, image in captures.items():
        screen = screens[number]
        x, y = screen.left - bounds.left, screen.top - bounds.top
        height, width = min(image.shape[0], bounds.height - y), min(image.shape[1], bounds.width - x)
        desktop[y : y + height, x : x + width] = image[:height, :width]
    return desktop


def serve(connection: Connection, locate: Callable[..., Any]) -> None:
    """Answers the searches asked on the connection until it closes or asks to quit."""
    searches: queue.Queue[tuple | None] = queue.Queue()
    stop = threading.Event()

    def read() -> None:  # in its own thread, so that a stop arrives during a search
        try:
            while True:
                request = connection.recv()
                if request[0] == "stop":
                    stop.set()
                elif request[0] == "search":
                    searches.put(request)
                else:
                    break
        except (EOFError, OSError):
            pass
        searches.put(None)

    threading.Thread(target=read, daemon=True).start()
    while (request := searches.get()) is not None:
        _, element, captures, screens, mouse = request
        stop.clear()
        start = time.perf_counter()
        try:
            report = locate(element, grabber(captures, screens), screens, mouse, stop.is_set)
            answer: tuple = ("report", report, time.perf_counter() - start)
        except Exception as failure:  # noqa: BLE001 - any failure of the search goes back to the caller
            answer = ("error", str(failure) or type(failure).__name__)
        try:
            connection.send(answer)
        except (EOFError, OSError):
            return


def main() -> None:
    """Listens on a free local port, tells it on the output, then serves the one caller knowing the key."""
    key = bytes.fromhex(sys.stdin.readline().strip())
    with Listener(("127.0.0.1", 0), authkey=key) as listener:
        print(listener.address[1], flush=True)
        _silence_output()  # nobody reads it any more: the detection's logs must not fill the pipe
        module, name = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOCATE).split(":")
        with listener.accept() as connection:
            serve(connection, getattr(import_module(module), name))


def _silence_output() -> None:
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115 - for the life of the process


if __name__ == "__main__":
    main()
