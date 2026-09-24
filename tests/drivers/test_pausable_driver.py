import threading
import time

import pytest

from guimauve.drivers.pausable_driver import PausableDriver
from guimauve.enums import Button, Key


class FakePauseManager:
    def __init__(self):
        self._running = threading.Event()
        self._running.set()

    def pause(self):
        self._running.clear()

    def resume(self):
        self._running.set()

    def is_paused(self):
        return not self._running.is_set()

    def wait_while_paused(self):
        self._running.wait()


@pytest.fixture
def pause_manager():
    return FakePauseManager()


@pytest.fixture
def driver(fake_driver, pause_manager):
    return PausableDriver(fake_driver, pause_manager)


def _hold_inputs(driver, fake_driver):
    driver.mouse_move(10, 20)
    driver.key_down(Key.CTRL)
    driver.mouse_down(Button.LEFT)
    fake_driver.calls.clear()


def _run_paused(fake_driver, pause_manager, target, threads=1):
    workers = [threading.Thread(target=target) for _ in range(threads)]
    pause_manager.pause()
    for worker in workers:
        worker.start()
    time.sleep(0.1)
    fake_driver.position = (999, 999)  # the user moves the mouse during the pause
    pause_manager.resume()
    for worker in workers:
        worker.join(timeout=1)


RESTORE_SEQUENCE = [
    ("mouse_up", Button.LEFT),
    ("key_up", Key.CTRL),
    ("mouse_move", 10, 20),
    ("key_down", Key.CTRL),
    ("mouse_down", Button.LEFT),
]


def test_delegates_when_not_paused(driver, fake_driver):
    driver.mouse_scroll(1, 0)
    driver.type("a")

    assert fake_driver.calls == [("mouse_scroll", 1, 0), ("type", "a")]


def test_pause_releases_then_restores_before_action(driver, fake_driver, pause_manager):
    _hold_inputs(driver, fake_driver)
    _run_paused(fake_driver, pause_manager, lambda: driver.mouse_up(Button.LEFT))
    assert fake_driver.calls == RESTORE_SEQUENCE + [("mouse_up", Button.LEFT)]


def test_concurrent_pause_restores_once(driver, fake_driver, pause_manager):
    _hold_inputs(driver, fake_driver)
    _run_paused(fake_driver, pause_manager, driver.capture, threads=3)
    assert fake_driver.calls == RESTORE_SEQUENCE + [("capture", None)] * 3


def test_suspended_time_counted_once_for_concurrent_threads(driver, fake_driver, pause_manager):
    _run_paused(fake_driver, pause_manager, driver.capture, threads=3)
    assert 0.1 <= driver.suspended_time < 0.2


def test_suspended_releases_immediately(driver, fake_driver):
    _hold_inputs(driver, fake_driver)

    with driver.suspended():
        assert fake_driver.calls == RESTORE_SEQUENCE[:2]

    assert fake_driver.calls == RESTORE_SEQUENCE


def test_suspended_skips_pause_checks(driver, fake_driver, pause_manager):
    pause_manager.pause()

    with driver.suspended():
        driver.capture()  # would block forever if the pause was applied

    assert ("capture", None) in fake_driver.calls


def test_nested_suspensions_restore_once(driver, fake_driver):
    _hold_inputs(driver, fake_driver)

    with driver.suspended():
        with driver.suspended():
            pass
        assert len(fake_driver.calls) == 2

    assert fake_driver.calls == RESTORE_SEQUENCE


def test_released_inputs_are_not_restored(driver, fake_driver, pause_manager):
    driver.key_down(Key.CTRL)
    driver.key_up(Key.CTRL)
    fake_driver.calls.clear()

    with driver.suspended():
        pass

    assert ("key_down", Key.CTRL) not in fake_driver.calls


def test_close_releases_held_inputs(driver, fake_driver):
    _hold_inputs(driver, fake_driver)
    driver.close()
    assert fake_driver.calls == RESTORE_SEQUENCE[:2] + [("close",)]
