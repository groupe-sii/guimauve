import pytest

from guimauve.gui.element_editor_next.state import (
    ELEMENT,
    Document,
    SetTrial,
    apply_trials,
    discard_trials,
    remove,
    resolve,
)
from guimauve.models.element import Element
from guimauve.models.parameters import Parameters
from guimauve.models.variant import TextVariant


@pytest.fixture
def document():
    return Document(
        Element(
            name="button",
            mouse_speed=200,
            variants=[TextVariant(name="label", text="OK"), TextVariant(name="short", text="O")],
        )
    )


def key(document, index):
    return document.key(document.variants[index])


def test_trial_is_set_then_undone(document):
    command = SetTrial(ELEMENT, "mouse_speed", 300)

    command.do(document)
    assert document.trials.element == {"mouse_speed": 300}

    command.undo(document)
    assert document.trials.element == {}


def test_undo_restores_previous_trial(document):
    SetTrial(ELEMENT, "mouse_speed", 300).do(document)
    command = SetTrial(ELEMENT, "mouse_speed", 400)

    command.do(document)
    command.undo(document)

    assert document.trials.element == {"mouse_speed": 300}


def test_none_removes_trial_and_empty_variant_entry(document):
    variant = key(document, 0)
    SetTrial(variant, "text_confidence_threshold", 0.5).do(document)
    command = SetTrial(variant, "text_confidence_threshold", None)

    command.do(document)
    assert document.trials.variants == {}
    assert document.trials.is_empty

    command.undo(document)
    assert document.trials.variants == {variant: {"text_confidence_threshold": 0.5}}


def test_trial_gestures_merge():
    first = SetTrial(ELEMENT, "mouse_speed", 300, gesture=1)

    assert first.merge(SetTrial(ELEMENT, "mouse_speed", 400, gesture=1))
    assert first.value == 400
    assert not first.merge(SetTrial(ELEMENT, "mouse_speed", 500, gesture=2))


def test_trials_do_not_modify_element(document):
    SetTrial(ELEMENT, "mouse_speed", 300).do(document)

    assert document.element.mouse_speed == 200
    assert not document.is_modified()


def test_cascade_uses_document_trials_by_default(document):
    SetTrial(ELEMENT, "mouse_speed", 300).do(document)
    default = Parameters().default

    assert resolve("mouse_speed", document, default).value == 300


def test_apply_writes_values_and_clears_trials(document):
    variant = key(document, 1)
    SetTrial(ELEMENT, "mouse_speed", 300).do(document)
    SetTrial(variant, "text_confidence_threshold", 0.5).do(document)
    command = apply_trials(document)

    command.do(document)

    assert document.element.mouse_speed == 300
    assert document.variants[1].text_confidence_threshold == 0.5
    assert document.trials.is_empty
    assert document.is_modified()


def test_undo_apply_restores_element_and_trials(document):
    SetTrial(ELEMENT, "mouse_speed", 300).do(document)
    command = apply_trials(document)

    command.do(document)
    command.undo(document)

    assert document.element.mouse_speed == 200
    assert document.trials.element == {"mouse_speed": 300}
    assert not document.is_modified()


def test_apply_skips_removed_variant(document):
    removed = document.variants[1]
    SetTrial(document.key(removed), "text_confidence_threshold", 0.5).do(document)
    remove(document, ELEMENT, "variants", document.key(removed)).do(document)

    apply_trials(document).do(document)

    assert removed.text_confidence_threshold is None
    assert document.trials.is_empty


def test_discard_then_undo(document):
    SetTrial(ELEMENT, "mouse_speed", 300).do(document)
    command = discard_trials(document)

    command.do(document)
    assert document.trials.is_empty

    command.undo(document)
    assert document.trials.element == {"mouse_speed": 300}
