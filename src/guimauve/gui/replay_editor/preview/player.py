"""Orchestrates every preview renderer.

Owns a QTimer for real-time play, and exposes :meth:`set_time` for
scrubbing. Purely visual — never triggers any OS action; the real
replay lives in :class:`ReplayService`.
"""

import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QGraphicsScene

from guimauve.gui.replay_editor.constants import SCROLL_FADE
from guimauve.gui.replay_editor.preview.compute import (
    ScrollBatch,
    compute_double_clicks,
    compute_drags,
    compute_scroll_batches,
    cursor_position_at,
)
from guimauve.gui.replay_editor.preview.cursor import CursorRenderer
from guimauve.gui.replay_editor.preview.drags import DragRenderer
from guimauve.gui.replay_editor.preview.keyboard_state import active_keys_at
from guimauve.gui.replay_editor.preview.ripples import RippleRenderer
from guimauve.gui.replay_editor.widgets.keyboard_overlay import KeyboardOverlay
from guimauve.models.input_event import InputEvent


class PreviewPlayer(QObject):
    """Drives a visual replay of an event list over a QGraphicsScene.

    :cvar time_changed: Emitted with the current time in seconds every
        timer tick, and on :meth:`set_time` / :meth:`reset`.
    :cvar finished: Emitted once when the playhead reaches the end of
        the recording during real-time playback.
    """

    time_changed = Signal(float)
    finished = Signal()

    def __init__(
        self,
        scene: QGraphicsScene,
        overlay: KeyboardOverlay | None = None,
        parent: QObject | None = None,
    ) -> None:
        """
        :param scene: The scene on which every renderer draws.
        :param overlay: Optional keyboard overlay stacked over the
            scene's view. Passing ``None`` disables keyboard display.
        :param parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._scene = scene
        self._overlay = overlay

        self._events: list[InputEvent] = []
        self._first_t: float = 0.0
        self._duration: float = 0.0
        self._scroll_batches: list[ScrollBatch] = []

        self._current_t: float = 0.0
        self._playing: bool = False
        self._wall_start: float | None = None
        self._time_at_start: float = 0.0

        self._cursor = CursorRenderer(scene)
        self._ripples = RippleRenderer(scene, self._cursor_position_at)
        self._drags = DragRenderer(scene)

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._on_tick)

    def set_events(self, events: list[InputEvent]) -> None:
        """Load a new event list and reset the playhead to 0.

        :param events: The events to replay. An empty list puts the
            player in an idle state.
        """
        self.pause()
        self._events = list(events) if events else []
        if self._events:
            self._first_t = self._events[0].t
            self._duration = max(0.0, self._events[-1].t - self._first_t)
        else:
            self._first_t = 0.0
            self._duration = 0.0

        self._scroll_batches = compute_scroll_batches(self._events, self._first_t)
        double_clicks = compute_double_clicks(self._events, self._first_t)
        self._ripples.set_events(self._events, self._first_t, double_clicks)
        self._drags.set_drags(compute_drags(self._events, self._first_t, self._duration))

        self.set_time(0)

    def is_playing(self) -> bool:
        """:return: ``True`` if playback is currently running."""
        return self._playing

    def play(self) -> None:
        """Start (or resume) real-time playback.

        No-op if the player has no events or is already playing. If
        the playhead is at the end, restarts from the beginning.
        """
        if not self._events or self._playing:
            return
        if self._current_t >= self._duration:
            self._current_t = 0.0
        self._time_at_start = self._current_t
        self._wall_start = time.perf_counter()
        self._playing = True
        self._timer.start()

    def pause(self) -> None:
        """Pause playback; renderers keep their last state."""
        if not self._playing:
            return
        self._playing = False
        self._timer.stop()

    def reset(self) -> None:
        """Pause and jump back to time 0, emitting :data:`time_changed`."""
        self.pause()
        self.set_time(0)
        self.time_changed.emit(0.0)

    def set_time(self, seconds: float) -> None:
        """Jump the playhead to a specific time (used for scrubbing).

        :param seconds: Target time in seconds; clamped to
            ``[0, duration]``.
        """
        self._current_t = max(0.0, min(float(seconds), self._duration))
        if self._playing:
            self._wall_start = time.perf_counter()
            self._time_at_start = self._current_t
        self._render()

    def _on_tick(self) -> None:
        """Advance the playhead by real elapsed time and re-render."""
        assert self._wall_start is not None
        elapsed = time.perf_counter() - self._wall_start
        self._current_t = self._time_at_start + elapsed
        if self._current_t >= self._duration:
            self._current_t = self._duration
            self._render()
            self.time_changed.emit(self._current_t)
            self.pause()
            self.finished.emit()
            return
        self._render()
        self.time_changed.emit(self._current_t)

    def _render(self) -> None:
        """Refresh every renderer for the current playhead position."""
        if not self._events:
            self._cursor.hide()
            self._ripples.clear()
            self._drags.clear()
            if self._overlay is not None:
                self._overlay.show_keys(None, 0.0)
            return

        pos = self._cursor_position_at(self._current_t)
        scroll_dir = self._scroll_direction_at(self._current_t)
        self._cursor.render(pos, scroll_dir)
        self._ripples.render(self._current_t)
        self._drags.render(self._current_t)

        if self._overlay is not None:
            keys, opacity = active_keys_at(self._events, self._first_t, self._current_t)
            self._overlay.show_keys(keys, opacity)

    def _scroll_direction_at(self, current_t: float) -> int | None:
        """Look up the scroll direction active at ``current_t``.

        pynput / Windows reports ``dy > 0`` when the page content moves
        down (mouse wheel rotated toward the user with natural scrolling
        on, or just the platform's normal convention on some setups),
        so we flip the sign to match the user's mental model where
        ``+1`` means "arrow pointing down" (content going down).

        :param current_t: Relative time in seconds.
        :return: ``+1`` for down, ``-1`` for up, ``None`` outside any
            scroll batch (including during the ``SCROLL_FADE`` tail).
        """
        for batch in self._scroll_batches:
            if batch["start"] <= current_t <= batch["end"] + SCROLL_FADE:
                return 1 if batch["dy_sum"] >= 0 else -1
        return None

    def _cursor_position_at(self, current_t: float) -> tuple[int, int] | None:
        """Look up the cursor position at ``current_t``.

        :param current_t: Relative time in seconds.
        :return: ``(x, y)`` in scene units, or ``None`` if no
            ``mouse_move`` has been recorded yet.
        """
        return cursor_position_at(self._events, self._first_t, current_t)
