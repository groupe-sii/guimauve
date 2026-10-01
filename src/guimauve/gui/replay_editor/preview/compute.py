"""Pure event pre-computation for the preview player.

No Qt, no state — takes a list of :class:`InputEvent` and produces the
data structures the renderers consume. Testable on its own.
"""

from typing import TypedDict

from guimauve.gui.replay_editor.constants import (
    DOUBLE_CLICK_MAX_DISTANCE,
    DOUBLE_CLICK_MAX_INTERVAL,
    SCROLL_BATCH_GAP,
)
from guimauve.models.input_event import InputEvent


class ScrollBatch(TypedDict):
    """A group of consecutive scroll events treated as a single gesture."""

    start: float
    end: float
    dy_sum: int


class Drag(TypedDict):
    """A single mouse-drag gesture and its recorded points."""

    button: str
    start_t: float
    end_t: float | None
    points: list[tuple[float, int, int]]


def _button_name(ev: InputEvent) -> str:
    """Extract a button name from a mouse event, tolerating raw strings.

    :param ev: The mouse event to inspect.
    :return: The ``.name`` attribute of the button enum if present,
        otherwise the string representation of the raw argument.
    """
    return ev.args[0].name if hasattr(ev.args[0], "name") else str(ev.args[0])


def compute_scroll_batches(
    events: list[InputEvent],
    first_t: float,
) -> list[ScrollBatch]:
    """Group consecutive scroll events into batches separated by silences.

    Two scrolls closer than :data:`SCROLL_BATCH_GAP` belong to the same
    batch. ``dy_sum`` accumulates the vertical delta so the arrow's
    direction reflects the batch as a whole.

    :param events: All recorded events, in order.
    :param first_t: Timestamp of the first event in the recording,
        used to compute relative times.
    :return: The list of scroll batches, in chronological order.
    """
    batches: list[ScrollBatch] = []
    current: ScrollBatch | None = None
    for ev in events:
        if ev.action != "mouse_scroll":
            continue
        t = ev.t - first_t
        dy = ev.args[1] or ev.args[0]
        if current is not None and t - current["end"] <= SCROLL_BATCH_GAP:
            current["end"] = t
            current["dy_sum"] += dy
        else:
            if current is not None:
                batches.append(current)
            current = {"start": t, "end": t, "dy_sum": dy}
    if current is not None:
        batches.append(current)
    return batches


def compute_drags(
    events: list[InputEvent],
    first_t: float,
    duration: float,
) -> list[Drag]:
    """Reconstruct drag gestures from mouse_down / move / up sequences.

    A drag is retained only if it contains at least 3 recorded points,
    to filter out plain clicks with no movement.

    :param events: All recorded events, in order.
    :param first_t: Timestamp of the first event in the recording.
    :param duration: Full duration of the recording, used as the
        end time for drags still active at the recording's end.
    :return: The list of drag gestures, in chronological order.
    """
    drags: list[Drag] = []
    active: dict[str, Drag] = {}
    last_pos: tuple[int, int] | None = None

    for ev in events:
        rel_t = ev.t - first_t
        if ev.action == "mouse_move":
            last_pos = (ev.args[0], ev.args[1])
            for drag in active.values():
                drag["points"].append((rel_t, last_pos[0], last_pos[1]))
        elif ev.action == "mouse_down":
            button = _button_name(ev)
            active[button] = {
                "button": button,
                "start_t": rel_t,
                "end_t": None,
                "points": [(rel_t, last_pos[0], last_pos[1])] if last_pos else [],
            }
        elif ev.action == "mouse_up":
            button = _button_name(ev)
            if button in active:
                drag = active.pop(button)
                drag["end_t"] = rel_t
                if last_pos:
                    drag["points"].append((rel_t, last_pos[0], last_pos[1]))
                if len(drag["points"]) >= 3:
                    drags.append(drag)

    for drag in active.values():
        if len(drag["points"]) >= 3:
            drag["end_t"] = duration
            drags.append(drag)
    return drags


def compute_double_clicks(
    events: list[InputEvent],
    first_t: float,
) -> set[int]:
    """Return the indices of ``mouse_down`` events that close a double click.

    A double click is two ``mouse_down`` of the same button within
    :data:`DOUBLE_CLICK_MAX_INTERVAL` seconds and less than
    :data:`DOUBLE_CLICK_MAX_DISTANCE` scene units apart.

    :param events: All recorded events, in order.
    :param first_t: Timestamp of the first event in the recording.
    :return: Set of event indices (into ``events``) whose ``mouse_down``
        closes a double click.
    """
    double_clicks: set[int] = set()
    last_downs: dict[str, tuple[float, tuple[int, int] | None]] = {}
    last_pos: tuple[int, int] | None = None

    for i, ev in enumerate(events):
        rel_t = ev.t - first_t
        if ev.action == "mouse_move":
            last_pos = (ev.args[0], ev.args[1])
        elif ev.action == "mouse_down":
            button = _button_name(ev)
            prev = last_downs.get(button)
            if prev and last_pos:
                prev_t, prev_pos = prev
                dt = rel_t - prev_t
                if dt <= DOUBLE_CLICK_MAX_INTERVAL and prev_pos:
                    dist = ((last_pos[0] - prev_pos[0]) ** 2 + (last_pos[1] - prev_pos[1]) ** 2) ** 0.5
                    if dist <= DOUBLE_CLICK_MAX_DISTANCE:
                        double_clicks.add(i)
            last_downs[button] = (rel_t, last_pos)
    return double_clicks


def cursor_position_at(
    events: list[InputEvent],
    first_t: float,
    current_t: float,
) -> tuple[int, int] | None:
    """Return the last known cursor position at ``current_t``.

    :param events: All recorded events, in order.
    :param first_t: Timestamp of the first event in the recording.
    :param current_t: Relative time (from ``first_t``) at which to
        sample the cursor position.
    :return: ``(x, y)`` in scene units, or ``None`` if no ``mouse_move``
        has been recorded yet at ``current_t``.
    """
    target = first_t + current_t
    last_move: InputEvent | None = None
    for ev in events:
        if ev.t > target:
            break
        if ev.action == "mouse_move":
            last_move = ev
    if last_move is None:
        return None
    return last_move.args[0], last_move.args[1]
