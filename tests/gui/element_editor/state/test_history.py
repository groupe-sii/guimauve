import pytest

from guimauve.gui.element_editor_next.state import ELEMENT, Document, History, SetValue
from guimauve.models.element import Element


@pytest.fixture
def document():
    return Document(Element(name="button", timeout=3))


@pytest.fixture
def history(document):
    return History(document)


def test_push_runs_command(history, document):
    history.push(SetValue(ELEMENT, "timeout", 4))

    assert document.element.timeout == 4
    assert history.can_undo and not history.can_redo


def test_undo_then_redo(history, document):
    history.push(SetValue(ELEMENT, "timeout", 4, "Timeout"))

    assert history.undo().label == "Timeout"
    assert document.element.timeout == 3
    assert history.redo_label == "Timeout"

    history.redo()
    assert document.element.timeout == 4
    assert history.undo_label == "Timeout"


def test_nothing_to_undo_or_redo(history):
    assert history.undo() is None
    assert history.redo() is None
    assert history.undo_label is None and history.redo_label is None


def test_new_command_clears_redo(history):
    history.push(SetValue(ELEMENT, "timeout", 4))
    history.undo()

    history.push(SetValue(ELEMENT, "timeout", 5))

    assert not history.can_redo


def test_gesture_is_undone_in_one_step(history, document):
    for value in (4, 5, 6):
        history.push(SetValue(ELEMENT, "timeout", value, gesture=1))

    history.undo()

    assert document.element.timeout == 3
    assert not history.can_undo


def test_separate_gestures_are_undone_separately(history, document):
    history.push(SetValue(ELEMENT, "timeout", 4, gesture=1))
    history.push(SetValue(ELEMENT, "timeout", 5, gesture=2))

    history.undo()

    assert document.element.timeout == 4


def test_undoing_everything_leaves_document_unmodified(history, document):
    history.push(SetValue(ELEMENT, "timeout", 4))
    history.push(SetValue(ELEMENT, "mouse_speed", 100))

    history.undo()
    history.undo()

    assert not document.is_modified()
