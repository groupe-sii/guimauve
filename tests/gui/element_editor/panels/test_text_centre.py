import numpy as np
import pytest
from PySide6.QtCore import Qt

from guimauve.gui.element_editor_next.panels import TextCentre
from guimauve.gui.element_editor_next.state import Mode, TestResult, TestScope
from guimauve.models.variant import ImageVariant, TextVariant

EMPTY = "Must not be empty"


@pytest.fixture
def store(make_store):
    return make_store(
        [
            TextVariant(name="label", text="Sign in"),
            TextVariant(name="title", text="Welcome"),
            ImageVariant(name="light", image=np.zeros((40, 120, 3), np.uint8)),
        ]
    )


@pytest.fixture
def centre(qtbot, theme, store):
    centre = TextCentre(store, theme)
    qtbot.addWidget(centre)
    centre.show()
    store.select(key(store, 0))
    return centre


def key(store, index: int) -> int:
    return store.variant_keys()[index]


def text(store, index: int = 0) -> str:
    return store.document.get(key(store, index)).text


def type_over(qtbot, centre, typed: str) -> None:
    centre.field.focus_text()
    qtbot.keyClicks(centre.field.input, typed)


def test_shows_the_text_of_the_selected_text_variant(store, centre):
    assert centre.isVisible()
    assert centre.field.text() == "Sign in"
    store.select(key(store, 1))
    assert centre.field.text() == "Welcome"


@pytest.mark.parametrize("index", [2, None])
def test_hidden_without_a_text_variant(store, centre, index):
    store.select(None if index is None else key(store, index))
    assert centre.isHidden()


def test_each_key_sets_the_text_and_the_edit_is_one_undo_step(qtbot, store, centre):
    type_over(qtbot, centre, "Log in")
    assert text(store) == "Log in"

    store.undo()

    assert text(store) == centre.field.text() == "Sign in"
    assert not store.can_undo


def test_the_edit_ends_without_leading_and_trailing_spaces_in_the_same_step(qtbot, store, centre):
    centre.field.input.end(False)
    qtbot.keyClicks(centre.field.input, " now ")
    qtbot.keyClick(centre.field.input, Qt.Key.Key_Return)

    assert text(store) == centre.field.text() == "Sign in now"
    store.undo()
    assert text(store) == "Sign in"
    assert not store.can_undo


def test_an_edit_that_changes_nothing_adds_no_step(qtbot, store, centre):
    qtbot.keyClick(centre.field.input, Qt.Key.Key_Return)
    assert not store.can_undo


def test_an_undo_while_typing_ends_the_edit(qtbot, store, centre):
    centre.field.input.end(False)
    qtbot.keyClicks(centre.field.input, "x")
    store.undo()
    qtbot.keyClicks(centre.field.input, "y")

    assert text(store) == "Sign iny"
    store.undo()
    assert text(store) == "Sign in"
    assert not store.can_undo


def test_another_variant_starts_another_step(qtbot, store, centre):
    type_over(qtbot, centre, "Log in")
    store.select(key(store, 1))
    type_over(qtbot, centre, "Hello")

    store.undo()
    assert (text(store, 0), text(store, 1)) == ("Log in", "Welcome")


def test_an_empty_text_shows_its_error(qtbot, store, centre):
    centre.field.focus_text()
    qtbot.keyClick(centre.field.input, Qt.Key.Key_Backspace)
    assert text(store) == ""
    assert centre.field.input.property("invalid") is True
    assert store.issues_of(key(store, 0), "text")[0].message == EMPTY

    qtbot.keyClicks(centre.field.input, "OK")
    assert centre.field.input.property("invalid") is False


def test_spaces_only_end_as_an_empty_text_in_error(qtbot, store, centre):
    type_over(qtbot, centre, "   ")
    qtbot.keyClick(centre.field.input, Qt.Key.Key_Return)
    assert text(store) == ""
    assert centre.field.input.property("invalid") is True


def test_a_request_gives_the_focus_to_the_text(qtbot, store, centre):
    centre.activateWindow()
    qtbot.waitUntil(centre.isActiveWindow)

    store.request_text_edit()

    assert centre.field.input.hasFocus()
    assert centre.field.input.selectedText() == "Sign in"


def test_a_request_without_a_text_variant_takes_no_focus(qtbot, store, centre):
    centre.activateWindow()
    qtbot.waitUntil(centre.isActiveWindow)
    store.select(key(store, 2))

    store.request_text_edit()

    assert not centre.field.input.hasFocus()


def test_in_test_mode_the_text_is_read_only(qtbot, store, centre):
    store.set_mode(Mode.TEST)
    type_over(qtbot, centre, "Log in")

    assert text(store) == "Sign in"
    assert not centre.hint.isVisible() and not centre.not_tested.isVisible()


def test_edit_mode_points_to_the_test_until_one_ran(store, centre):
    assert centre.hint.isVisible() and centre.not_tested.isVisible()

    store.set_test_result(TestResult(TestScope.VARIANT, key(store, 0), None))

    assert centre.hint.isVisible() and not centre.not_tested.isVisible()
