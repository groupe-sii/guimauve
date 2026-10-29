import pytest

from guimauve.detection.detector import Match, Point
from guimauve.gui.element_editor_next.state import ELEMENT, Mode, TestResult, TestScope


def result(**fields) -> TestResult:
    return TestResult(TestScope.ELEMENT, None, None, **fields)


@pytest.fixture
def signals(store):
    emitted: list[str] = []
    for name in ("mode_changed", "test_changed"):
        getattr(store, name).connect(lambda name=name: emitted.append(name))
    return emitted


def test_scope_is_the_variant_by_default(store):
    assert store.test_scope is TestScope.VARIANT


def test_scope_change_keeps_the_result_fresh(store, signals):
    store.set_test_result(result())
    signals.clear()

    store.set_test_scope(TestScope.ELEMENT)
    store.set_test_scope(TestScope.ELEMENT)

    assert store.test_scope is TestScope.ELEMENT and not store.test_stale
    assert signals == ["mode_changed"]


def test_include_code_change_makes_the_result_stale(store, signals):
    store.set_test_result(result())
    signals.clear()

    store.set_include_code(False)

    assert store.test_stale
    assert signals == ["mode_changed", "test_changed"]


def test_tested_element_keeps_the_selected_variant(store):
    store.select(store.variant_keys()[1])

    assert [variant.name for variant in store.tested_element().variants] == ["dark"]


def test_tested_element_has_every_variant_for_the_element(store):
    store.set_test_scope(TestScope.ELEMENT)

    assert [variant.name for variant in store.tested_element().variants] == ["light", "dark"]


def test_tested_element_has_no_variant_without_selection(store):
    store.select(None)

    assert store.tested_element().variants == []


def test_tested_element_applies_the_trials_even_in_edit_mode(make_store):
    store = make_store(timeout=3)
    store.set_mode(Mode.TEST)
    store.set_field(ELEMENT, "template_confidence_threshold", 0.4)
    store.set_mode(Mode.EDIT)

    assert store.tested_element().variants[0].template_confidence_threshold == 0.4


def test_tested_element_follows_include_code(store):
    assert store.tested_element().mouse_speed == 500

    store.set_include_code(False)
    assert store.tested_element().mouse_speed == store.default.mouse_speed


def test_used_match():
    match = Match(None, Point(1, 2), 0.9)
    report = type("Report", (), {"matches": [match]})()

    assert TestResult(TestScope.VARIANT, 1, report, used=0).used_match is match
    assert TestResult(TestScope.VARIANT, 1, report).used_match is None
    assert result(error="Failed").used_match is None


def test_request_test(store, qtbot):
    with qtbot.waitSignal(store.test_requested):
        store.request_test()
