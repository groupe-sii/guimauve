import threading
from typing import Optional, Union

from pynput import keyboard, mouse
from pynput.keyboard import Key as PynputKey
from pynput.keyboard import KeyCode as PynputKeyCode

from guimauve.drivers.local.bindings import button_from_pynput, key_from_pynput
from guimauve.enums import Button, Key
from guimauve.models.input_event import InputEvent


class Recorder:
    """Record keyboard and mouse events in memory.

    Listens to keyboard and mouse events via ``pynput`` and stores them as
    timestamped :class:`InputEvent` objects. Recording stops when the
    ``stop_key`` passed to :meth:`wait` is pressed.

    A single Recorder instance can be reused across sessions: each call to
    :meth:`start` resets the event list.

    :ivar _events: Events captured during the current session.
    :vartype _events: list[InputEvent]
    """

    def __init__(self):
        self._events: list[InputEvent] = []
        self._keyboard = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._mouse = mouse.Listener(on_move=self._on_move, on_click=self._on_click, on_scroll=self._on_scroll)
        self._stop_signal = threading.Event()
        self._stop_key: Optional[Key] = None

    @property
    def events(self) -> list[InputEvent]:
        """Copy of the events captured during the current session."""
        return list(self._events)

    def start(self) -> None:
        """Reset the event list and start the listeners.

        Non-blocking: listeners run on their own threads. Call :meth:`wait`
        to block until the stop key is pressed.
        """
        self._events = []
        self._keyboard.start()
        self._mouse.start()
        self._stop_signal.clear()

    def wait(self, stop_key: Key) -> None:
        """Block until ``stop_key`` is pressed, then call :meth:`stop`.

        :param stop_key: Key whose press ends the recording session.
        """
        self._stop_key = stop_key
        self._stop_signal.wait()
        self.stop()

    def stop(self) -> None:
        """Stop the keyboard and mouse listeners.

        Recorded events remain accessible via ``self._events``.
        """
        self._keyboard.stop()
        self._mouse.stop()

    def _record(self, action: str, args: list) -> None:
        """Append a new :class:`InputEvent` timestamped with :func:`time.perf_counter`.

        :param action: Action name (e.g. ``"key_down"``, ``"mouse_move"``).
        :param args: Arguments associated with the action.
        """
        self._events.append(InputEvent(action=action, args=args))

    def _on_press(self, key: Optional[Union[PynputKey, PynputKeyCode]]) -> None:
        """Callback for key press events.

        Sets the stop signal if the key matches ``stop_key``, otherwise
        records a ``key_down`` event. Unknown keys are discarded.

        :param key: The pynput key that was pressed.
        """
        if (key := key_from_pynput(key)) is None:
            return

        if self._stop_key is not None and key is self._stop_key:
            self._stop_signal.set()
            return
        self._record("key_down", [key])

    def _on_release(self, key: Optional[Union[PynputKey, PynputKeyCode]]) -> None:
        """Callback for key release events. Unknown keys are discarded.

        :param key: The pynput key that was released.
        """
        if (key := key_from_pynput(key)) is None:
            return

        self._record("key_up", [key])

    def _on_move(self, x: int, y: int) -> None:
        """Callback for mouse motion events.

        :param x: Absolute X coordinate of the cursor.
        :param y: Absolute Y coordinate of the cursor.
        """
        self._record("mouse_move", [x, y])

    def _on_click(self, x: int, y: int, button: Button, pressed: bool) -> None:
        """Callback for mouse click events. Unknown buttons are discarded.

        :param x: Absolute X coordinate of the cursor.
        :param y: Absolute Y coordinate of the cursor.
        :param button: The pynput button involved.
        :param pressed: ``True`` if pressed, ``False`` if released.
        """
        if (button := button_from_pynput(button)) is None:
            return

        action = "mouse_down" if pressed else "mouse_up"
        self._record(action, [button])

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Callback for mouse scroll events.

        :param x: Absolute X coordinate of the cursor.
        :param y: Absolute Y coordinate of the cursor.
        :param dx: Horizontal scroll delta.
        :param dy: Vertical scroll delta.
        """
        self._record("mouse_scroll", [dy, dx])
