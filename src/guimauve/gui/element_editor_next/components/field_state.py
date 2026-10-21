"""What a property field shows, computed from the cascade; without Qt."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any

from guimauve.gui.element_editor_next.state import Issue, Resolution, Severity, Source

_OWN = {
    False: (Source.ELEMENT, Source.ELEMENT_TRIAL),
    True: (Source.VARIANT, Source.VARIANT_TRIAL),
}
_TRIALS = (Source.ELEMENT_TRIAL, Source.VARIANT_TRIAL)


@dataclass(frozen=True)
class FieldState:
    """Display of one field in the Element or Variant tab.

    :param value: Value in the editor: the own value when set, the inherited one otherwise; None when undefined.
        Never a value of the code, which is only shown beside the label.
    :param own: Set at the level of the tab: violet dot and reset.
    :param trial: The own value is a trial of the Test mode.
    :param inherited: Value saved below the tab without the own value, i.e. after a reset; never the code.
    :param source: Layer of the inherited value, for the tooltips; None when undefined.
    :param code: Value set in the code when it applies, shown beside the label; None otherwise.
    :param error: Message of the first error of the field.
    :param warning: Message of the first warning of the field.
    :param disabled_reason: Why the field has no effect; None when it has one.
    """

    value: Any
    own: bool = False
    trial: bool = False
    inherited: Any = None
    source: Source | None = None
    code: Any = None
    error: str | None = None
    warning: str | None = None
    disabled_reason: str | None = None


def field_state(
    resolution: Resolution,
    on_variant: bool = False,
    issues: Iterable[Issue] = (),
    disabled_reason: str | None = None,
) -> FieldState:
    """Translates the resolution of a field into what its row shows.

    :param on_variant: The row is in the Variant tab; in the Element tab otherwise.
    :param issues: Issues of this field, e.g. Store.issues_of(owner, field).
    """
    issues = list(issues)
    return replace(
        _value_state(resolution, on_variant),
        error=_first(issues, Severity.ERROR),
        warning=_first(issues, Severity.WARNING),
        disabled_reason=disabled_reason,
    )


def _value_state(resolution: Resolution, on_variant: bool) -> FieldState:
    layers = resolution.layers
    own = [source for source in _OWN[on_variant] if source in layers]
    # The code is not saved: it is shown beside the label while it applies, never in the editor.
    others = [source for source in layers if source not in _OWN[on_variant] and source is not Source.CODE]
    inherited = others[-1] if others else None
    code = layers[Source.CODE] if resolution.source is Source.CODE else None
    if not own:
        value = layers[inherited] if inherited else None
        return FieldState(value, inherited=value, source=inherited, code=code)

    top = own[-1]  # a trial wins over the value of its level
    return FieldState(
        layers[top],
        own=True,
        trial=top in _TRIALS,
        inherited=layers[inherited] if inherited else None,
        source=inherited,
        code=code,
    )


def _first(issues: list[Issue], severity: Severity) -> str | None:
    return next((issue.message for issue in issues if issue.severity is severity), None)
