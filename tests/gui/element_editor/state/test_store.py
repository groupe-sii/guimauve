import numpy as np
import pytest

from guimauve.drivers.driver import Screen
from guimauve.gui.element_editor_next.state import ELEMENT, Document, Mode, Store, remove
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters
from guimauve.models.variant import ImageVariant, Target, TextVariant


@pytest.fixture
def store():
    element = Element(
        name="button",
        timeout=3,
        variants=[
            ImageVariant(
                name="light",
                image=np.zeros((10, 20, 3), dtype=np.uint8),
                targets=[Target(name="icon", x=1, y=2), Target(name="arrow", x=3, y=4)],
            ),
            TextVariant(name="label", text="OK"),
            TextVariant(name="short", text="O"),
        ],
    )
    return Store(Document(element), Parameters().default)


@pytest.fixture
def signals(store):
    """Names of the signals emitted by the store, in order."""
    emitted: list[str] = []
    for name in ("document_changed", "selection_changed", "mode_changed", "test_changed"):
        getattr(store, name).connect(lambda name=name: emitted.append(name))
    return emitted


def key(store, index):
    return store.document.key(store.document.variants[index])


def remove_variant(store, index):
    store.execute(remove(store.document, ELEMENT, "variants", key(store, index)))


def test_first_variant_selected_at_opening(store):
    assert (store.selected_variant, store.selected_target) == (key(store, 0), None)


def test_no_selection_without_variant():
    store = Store(Document(Element(name="button", x=1, y=1)), Parameters().default)

    assert store.selected_variant is None


def test_set_field_notifies_and_updates_state(store, signals):
    store.set_field(ELEMENT, "timeout", 5, "Timeout")

    assert store.document.element.timeout == 5
    assert signals == ["document_changed"]
    assert store.is_modified and store.can_undo and store.undo_label == "Timeout"


def test_undo_and_redo_notify(store, signals):
    store.set_field(ELEMENT, "timeout", 5)

    store.undo()
    store.redo()

    assert signals == ["document_changed"] * 3
    assert store.document.element.timeout == 5


def test_nothing_to_undo_does_not_notify(store, signals):
    store.undo()
    store.redo()

    assert signals == []


def test_issues_are_updated_before_notification(store):
    seen = []
    store.document_changed.connect(lambda: seen.append(store.can_save))

    store.set_field(key(store, 1), "text", "")

    assert seen == [False]
    assert [issue.field for issue in store.issues_of(key(store, 1))] == ["text"]
    assert store.issues_of(key(store, 1), "name") == []


def test_gestures_are_merged(store):
    gesture = store.new_gesture()
    for value in (4, 5, 6):
        store.set_field(ELEMENT, "timeout", value, gesture=gesture)

    store.undo()

    assert store.document.element.timeout == 3
    assert store.new_gesture() != gesture


def test_select(store, signals):
    variant = store.document.variants[0]
    target = store.document.key(variant.targets[1])

    store.select(key(store, 0), target)
    store.select(key(store, 0), target)

    assert (store.selected_variant, store.selected_target) == (key(store, 0), target)
    assert signals == ["selection_changed"]


def test_selection_does_not_go_through_history(store):
    store.select(key(store, 1))

    assert not store.can_undo


def test_removing_selected_variant_selects_next(store):
    store.select(key(store, 1))
    following = key(store, 2)

    remove_variant(store, 1)

    assert store.selected_variant == following


def test_removing_last_selected_variant_selects_previous(store):
    store.select(key(store, 2))
    previous = key(store, 1)

    remove_variant(store, 2)

    assert store.selected_variant == previous


def test_removing_every_variant_clears_selection(store):
    for _ in range(3):
        remove_variant(store, 0)

    assert store.selected_variant is None


def test_undo_does_not_move_a_valid_selection(store):
    store.select(key(store, 2))
    store.set_field(ELEMENT, "timeout", 5)

    store.undo()

    assert store.selected_variant == key(store, 2)


def test_removing_selected_target_clears_it(store):
    variant = store.document.variants[0]
    target = store.document.key(variant.targets[0])
    store.select(key(store, 0), target)

    store.execute(remove(store.document, key(store, 0), "targets", target))

    assert (store.selected_variant, store.selected_target) == (key(store, 0), None)


def test_mode(store, signals):
    store.set_mode(Mode.TEST)
    store.set_mode(Mode.TEST)

    assert store.mode is Mode.TEST
    assert signals == ["mode_changed"]


def test_test_result_becomes_stale_once(store, signals):
    store.set_test_result("report")
    store.set_field(ELEMENT, "timeout", 5)
    store.set_field(ELEMENT, "timeout", 6)

    assert store.test_result == "report" and store.test_stale
    assert signals == ["test_changed", "document_changed", "test_changed", "document_changed"]


def test_new_test_result_is_fresh(store):
    store.set_test_result("old")
    store.set_field(ELEMENT, "timeout", 5)

    store.set_test_result("new")

    assert not store.test_stale


def test_result_is_a_copy_without_code_overrides(store):
    store.document.code_overrides["timeout"] = 1
    store.set_field(ELEMENT, "timeout", 5)

    result = store.result()
    result.timeout = 9

    assert store.document.element.timeout == 5
    assert result.variants[0].image is not None


def test_result_strips_the_texts_of_the_text_variants(store):
    store.set_field(key(store, 1), "text", "  OK ")

    assert store.result().variants[1].text == "OK"
    assert store.document.get(key(store, 1)).text == "  OK "


@pytest.fixture
def testing(store):
    store.set_mode(Mode.TEST)
    return store


def test_property_becomes_a_trial_in_testing(testing):
    testing.set_field(ELEMENT, "timeout", 5)

    assert testing.document.trials.element == {"timeout": 5}
    assert testing.document.element.timeout == 3
    assert testing.has_trials and not testing.is_modified


def test_variant_property_becomes_a_variant_trial(testing):
    testing.set_field(key(testing, 1), "text_confidence_threshold", 0.5)

    assert testing.document.trials.variants == {key(testing, 1): {"text_confidence_threshold": 0.5}}


@pytest.mark.parametrize(("field", "value"), [("name", "renamed"), ("text", "Cancel")])
def test_other_fields_are_set_in_testing(testing, field, value):
    testing.set_field(key(testing, 1), field, value)

    assert getattr(testing.document.variants[1], field) == value
    assert not testing.has_trials


def test_target_position_is_set_in_testing(testing):
    target = testing.document.variants[0].targets[0]

    testing.set_field(testing.document.key(target), "x", 5)

    assert target.x == 5
    assert not testing.has_trials


def test_trial_is_undoable_and_makes_test_stale(testing):
    testing.set_test_result("report")

    testing.set_field(ELEMENT, "timeout", 5)
    assert testing.test_stale

    testing.undo()
    assert not testing.has_trials


def test_apply_and_discard(testing):
    testing.set_field(ELEMENT, "timeout", 5)

    testing.apply_trials()
    assert testing.document.element.timeout == 5 and not testing.has_trials

    testing.undo()
    testing.discard_trials()
    assert testing.document.element.timeout == 3 and not testing.has_trials


def test_apply_without_trials_does_nothing(store):
    store.apply_trials()
    store.discard_trials()

    assert not store.can_undo


def test_trials_are_kept_back_in_edit_mode(testing):
    testing.set_field(ELEMENT, "timeout", 5)

    testing.set_mode(Mode.EDIT)

    assert testing.has_trials
    assert testing.result().timeout == 3


def test_include_code(store, signals):
    store.set_include_code(False)
    store.set_include_code(False)

    assert not store.include_code
    assert signals == ["mode_changed"]


def test_set_fields_is_one_step(store):
    store.set_fields(ELEMENT, {"x": 10, "rel_x": None}, "X")

    assert (store.document.element.x, store.undo_label) == (10, "X")
    store.undo()
    assert store.document.element.x is None
    assert not store.can_undo


def test_set_fields_in_test_mode_are_trials(store):
    store.set_mode(Mode.TEST)
    store.set_fields(ELEMENT, {"x": 10, "rel_x": None})

    assert store.document.trials.element == {"x": 10}  # a trial of None is no trial
    assert store.document.element.x is None


def test_screens_are_given_as_a_copy():
    screens = [Screen(0, 0, 1920, 1080), Screen(0, 0, 1920, 1080)]
    store = Store(Document(Element(name="button")), Parameters().default, screens)

    store.screens.clear()

    assert store.screens == screens
