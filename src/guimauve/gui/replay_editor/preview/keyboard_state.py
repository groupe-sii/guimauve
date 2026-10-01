"""Pure logic: given events + current time, what keys should we display?"""


from guimauve.gui.replay_editor.constants import (
    KEYBOARD_FADE,
    KEYBOARD_LINGER,
    MAX_TYPED_KEYS,
    MODIFIERS,
    SHORTCUT_MODIFIERS,
)
from guimauve.models.input_event import InputEvent


def active_keys_at(
    events: list[InputEvent],
    first_t: float,
    current_t: float,
) -> tuple[list[str] | None, float]:
    """Compute the keys to show on the overlay at a given time.

    Behavior:

    * Auto-repeats (Windows sends N ``key_down`` for a held key) are ignored.
    * Pressing a shortcut modifier (Ctrl/Alt/Meta) clears the typed-keys
      buffer, so the display focuses on the combo being built.
    * Shift stays in the modifier set without clearing (used for capitals).
    * Once nothing is held and no activity happens for
      ``KEYBOARD_LINGER + KEYBOARD_FADE`` seconds, the buffer resets.
    * Only the last :data:`MAX_TYPED_KEYS` typed keys are shown; older
      ones are elided with ``"..."``.

    :param events: All recorded events, in order.
    :param first_t: Timestamp of the first event in the recording.
    :param current_t: Relative time (from ``first_t``) at which to
        sample the keyboard state.
    :return: ``(display, opacity)`` where ``display`` is the list of
        key names to render (modifiers first, sorted) and ``opacity``
        is a fade factor in ``[0, 1]``. Returns ``(None, 0.0)`` when
        there is nothing to show.
    """
    target = first_t + current_t
    held: set[str] = set()
    combo_modifiers: set[str] = set()
    tap_history: list[str] = []
    last_release_t: float | None = None
    last_activity_t: float | None = None

    for ev in events:
        if ev.t > target:
            break
        if ev.action not in ("key_down", "key_up"):
            continue

        key = ev.args[0].name if hasattr(ev.args[0], "name") else str(ev.args[0])
        rel_t = ev.t - first_t

        if ev.action == "key_down":
            if key in held:
                continue

            if last_activity_t is not None and (rel_t - last_activity_t) > KEYBOARD_LINGER + KEYBOARD_FADE:
                tap_history = []
                combo_modifiers = set()

            held.add(key)
            if key in SHORTCUT_MODIFIERS:
                tap_history = []
                combo_modifiers.add(key)
            elif key in MODIFIERS:
                combo_modifiers.add(key)
            else:
                tap_history.append(key)

            last_activity_t = rel_t
        else:
            held.discard(key)
            last_release_t = rel_t
            last_activity_t = rel_t

    if not tap_history and not held and not combo_modifiers:
        return None, 0.0

    modifiers_sorted = sorted(combo_modifiers)
    if len(tap_history) > MAX_TYPED_KEYS:
        display = modifiers_sorted + ["..."] + tap_history[-MAX_TYPED_KEYS:]
    else:
        display = modifiers_sorted + tap_history

    if held:
        opacity = 1.0
    elif last_release_t is None:
        return None, 0.0
    else:
        age = current_t - last_release_t
        if age <= KEYBOARD_LINGER:
            opacity = 1.0
        elif age <= KEYBOARD_LINGER + KEYBOARD_FADE:
            opacity = 1.0 - (age - KEYBOARD_LINGER) / KEYBOARD_FADE
        else:
            return None, 0.0

    return display, opacity
