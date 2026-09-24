import threading

import pytest

from guimauve.drivers.local.bindings import KEY_MAP
from guimauve.enums import Key
from guimauve.pause_manager import PauseManager

SHORTCUT = [Key.CTRL, Key.SHIFT, Key.ALT]
CTRL, SHIFT, ALT = (KEY_MAP[key] for key in SHORTCUT)
OTHER = KEY_MAP[Key.ESC]


@pytest.fixture
def pause_manager(monkeypatch, fake_listener_cls):
    """PauseManager built with a fake listener so no real pynput code runs."""
    monkeypatch.setattr("guimauve.pause_manager.Listener", fake_listener_cls)
    return PauseManager(SHORTCUT)


def _press(pause_manager, *keys):
    for key in keys:
        pause_manager._on_key_press(key)


def _release(pause_manager, *keys):
    for key in keys:
        pause_manager._on_key_release(key)


def test_starts_running_with_listener(pause_manager):
    assert not pause_manager.is_paused()
    assert pause_manager._keyboard_listener.running


def test_pause_and_resume(pause_manager):
    pause_manager.pause()
    assert pause_manager.is_paused()

    pause_manager.resume()
    assert not pause_manager.is_paused()


def test_wait_while_paused_blocks_until_resume(pause_manager):
    pause_manager.pause()
    worker = threading.Thread(target=pause_manager.wait_while_paused)
    worker.start()

    worker.join(timeout=0.1)
    assert worker.is_alive()

    pause_manager.resume()
    worker.join(timeout=1)
    assert not worker.is_alive()


def test_full_shortcut_pauses(pause_manager):
    _press(pause_manager, CTRL, SHIFT, ALT)

    assert pause_manager.is_paused()


def test_partial_shortcut_does_nothing(pause_manager):
    _press(pause_manager, CTRL, SHIFT, OTHER)

    assert not pause_manager.is_paused()


def test_shortcut_order_does_not_matter(pause_manager):
    _press(pause_manager, ALT, CTRL, SHIFT)

    assert pause_manager.is_paused()


def test_released_key_breaks_shortcut(pause_manager):
    _press(pause_manager, CTRL, SHIFT)
    _release(pause_manager, CTRL)
    _press(pause_manager, ALT)

    assert not pause_manager.is_paused()


def test_second_shortcut_resumes(pause_manager):
    _press(pause_manager, CTRL, SHIFT, ALT)
    _release(pause_manager, CTRL, SHIFT, ALT)
    _press(pause_manager, CTRL, SHIFT, ALT)

    assert not pause_manager.is_paused()


def test_held_shortcut_auto_repeat_does_not_toggle_again(pause_manager):
    _press(pause_manager, CTRL, SHIFT, ALT)
    _press(pause_manager, ALT, ALT, ALT)  # keyboard auto-repeat while the shortcut is held

    assert pause_manager.is_paused()


def test_releasing_unpressed_key_is_ignored(pause_manager):
    _release(pause_manager, OTHER)

    assert not pause_manager.is_paused()
