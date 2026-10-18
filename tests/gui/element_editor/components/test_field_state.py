from guimauve.gui.element_editor_next.components.field_state import FieldState, field_state
from guimauve.gui.element_editor_next.state import ELEMENT, Issue, Resolution, Severity, Source


def resolution(**layers) -> Resolution:
    """Resolution from layers given by source name, from the weakest to the strongest."""
    by_source = {Source[name.upper()]: value for name, value in layers.items()}
    ordered = dict(sorted(by_source.items(), key=lambda item: list(Source).index(item[0])))
    source = list(ordered)[-1] if ordered else None
    return Resolution(ordered[source] if source else None, source, ordered)


def test_undefined():
    assert field_state(resolution()) == FieldState(None)


def test_inherited_from_the_default():
    assert field_state(resolution(default=5)) == FieldState(5, inherited=5, source=Source.DEFAULT)


def test_own_value_of_the_element():
    assert field_state(resolution(default=5, element=3)) == FieldState(3, own=True, inherited=5, source=Source.DEFAULT)


def test_code_applies_over_the_element():
    state = field_state(resolution(default=5, element=3, code=8))
    assert state == FieldState(3, own=True, inherited=8, source=Source.CODE, code=8)


def test_inherited_from_the_code():
    assert field_state(resolution(default=5, code=8)) == FieldState(8, inherited=8, source=Source.CODE, code=8)


def test_trial_wins_over_the_code():
    state = field_state(resolution(element=3, code=8, element_trial=4))
    assert (state.value, state.trial, state.code) == (4, True, None)


def test_variant_tab_inherits_from_the_element():
    state = field_state(resolution(default=5, element=3), on_variant=True)
    assert state == FieldState(3, inherited=3, source=Source.ELEMENT)


def test_variant_tab_inherits_from_the_code():
    state = field_state(resolution(element=3, code=8), on_variant=True)
    assert (state.value, state.source, state.code) == (8, Source.CODE, 8)


def test_variant_value_wins_over_the_code():
    state = field_state(resolution(element=3, code=8, variant=2), on_variant=True)
    assert state == FieldState(2, own=True, inherited=8, source=Source.CODE)


def test_variant_trial():
    state = field_state(resolution(variant=2, variant_trial=1), on_variant=True)
    assert (state.value, state.own, state.trial) == (1, True, True)


def test_issues_and_disabled_reason():
    issues = [
        Issue(Severity.WARNING, "Screen 3 is not connected", ELEMENT, "screen"),
        Issue(Severity.ERROR, "Must be at least 0", ELEMENT, "screen"),
    ]
    state = field_state(resolution(element=3), issues=issues, disabled_reason="No effect")
    assert state.error == "Must be at least 0"
    assert state.warning == "Screen 3 is not connected"
    assert state.disabled_reason == "No effect"
