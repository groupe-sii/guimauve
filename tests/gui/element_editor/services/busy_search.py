"""Searches run by the search process in the tests, imported by it as busy_search:<function>."""

import os
import time

from guimauve.detection.report import LocateReport


def hold(element, grab, screens, mouse, stopped) -> LocateReport:
    """Keeps Python busy without letting it go, as the OCR does, for about a second."""
    sum(range(50_000_000))  # one call into C: no other thread of this process runs meanwhile
    return LocateReport([])


def until_stopped(element, grab, screens, mouse, stopped) -> LocateReport:
    """Runs until stopped, at most 10 s, then fails as a stopped search does."""
    deadline = time.monotonic() + 10
    while not stopped() and time.monotonic() < deadline:
        time.sleep(0.01)
    raise RuntimeError("stopped" if stopped() else "never stopped")


def crash(element, grab, screens, mouse, stopped) -> LocateReport:
    os._exit(3)
