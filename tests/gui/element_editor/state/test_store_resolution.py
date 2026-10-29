import pytest

from guimauve.gui.element_editor_next.state import ELEMENT, Mode, Source

THRESHOLD = "template_confidence_threshold"


@pytest.fixture
def tried(make_store):
    """Store with saved values and trials over them, on the element and the first variant, back in Edit mode."""
    store = make_store(timeout=3)
    store.set_mode(Mode.TEST)
    store.set_field(ELEMENT, "timeout", 5)
    store.set_field(ELEMENT, THRESHOLD, 0.4)
    store.set_field(store.variant_keys()[0], THRESHOLD, 0.5)
    store.set_mode(Mode.EDIT)
    return store


def test_edit_shows_the_saved_value(tried):
    resolution = tried.resolve("timeout")

    assert (resolution.value, resolution.source) == (3, Source.ELEMENT)
    assert Source.ELEMENT_TRIAL not in resolution.layers


def test_test_shows_the_trial(tried):
    tried.set_mode(Mode.TEST)
    resolution = tried.resolve("timeout")

    assert (resolution.value, resolution.source) == (5, Source.ELEMENT_TRIAL)


def test_edit_ignores_the_trials_of_a_variant(tried):
    key = tried.variant_keys()[0]

    assert Source.VARIANT_TRIAL not in tried.resolve(THRESHOLD, key).layers

    tried.set_mode(Mode.TEST)
    assert tried.resolve(THRESHOLD, key).value == 0.5


def test_edit_always_shows_the_code(store):
    store.set_include_code(False)

    assert store.resolve("mouse_speed").source is Source.CODE

    store.set_mode(Mode.TEST)
    assert Source.CODE not in store.resolve("mouse_speed").layers


def test_test_shows_the_code_when_included(store):
    store.set_mode(Mode.TEST)

    assert store.resolve("mouse_speed").source is Source.CODE


def test_override_in_edit_copies_the_saved_value(tried):
    key = tried.variant_keys()[1]

    tried.override(key, THRESHOLD)

    assert getattr(tried.document.get(key), THRESHOLD) == tried.default.template_confidence_threshold
