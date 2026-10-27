from types import SimpleNamespace

import pytest

import guimauve.gui.element_editor_next as next_editor
from guimauve.gui.element_editor_next import EditorResult, ResumeMode
from guimauve.models.element import Element


@pytest.fixture
def opened(monkeypatch, controller):
    """The new editor enabled and replaced by a recorder; set `opened.result` to choose what it returns."""
    opened = SimpleNamespace(contexts=[], persisted=[], result=EditorResult(None))

    def start(context):
        opened.contexts.append(context)
        return opened.result

    monkeypatch.setenv("GUIMAUVE_EDITOR", "next")
    monkeypatch.setattr(next_editor, "start_element_editor", start)
    monkeypatch.setattr(controller, "_persist_element", opened.persisted.append)
    return opened


def element() -> Element:
    return Element(name="button", x=1, y=1)(timeout=9)  # timeout set in the code for this call


def test_new_editor_gets_the_code_overrides_and_the_screens(controller, opened, fake_driver):
    controller._trigger_editor(element(), "ELEMENT NOT FOUND ON SCREEN")

    (context,) = opened.contexts
    assert context.code_overrides == {"timeout": 9}
    assert context.element.timeout is None  # the element as saved, without the code values
    assert context.screens == fake_driver.screens()
    assert context.message == "Element not found on screen"
    assert context.from_run
    assert context.mouse_position == tuple(fake_driver.mouse_position())


def test_saved_element_is_persisted_with_the_code_values_back(controller, opened):
    opened.result = EditorResult(Element(name="button", x=5, y=1), ResumeMode.AFTER_3_S)

    returned = controller._trigger_editor(element(), "INVALID ELEMENT")

    (saved,) = opened.persisted
    assert (saved.x, saved.timeout) == (5, None)
    assert (returned.x, returned.timeout) == (5, 9)


def test_skip_persists_nothing(controller, opened):
    assert controller._trigger_editor(element(), "INVALID ELEMENT") is None
    assert opened.persisted == []


def test_old_editor_without_the_variable(controller, monkeypatch):
    import guimauve.gui.element_editor as old_editor

    monkeypatch.delenv("GUIMAUVE_EDITOR", raising=False)
    calls = []
    monkeypatch.setattr(old_editor, "start_element_editor", lambda context: calls.append(context) or (None, False))

    assert controller._trigger_editor(element(), "INVALID ELEMENT") is None
    assert calls and not hasattr(calls[0], "code_overrides")
