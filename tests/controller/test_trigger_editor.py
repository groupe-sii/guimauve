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


def test_resumes_at_once(controller, opened, sleeps):
    opened.result = EditorResult(Element(name="button", x=5, y=1), ResumeMode.NOW)

    controller._trigger_editor(element(), "INVALID ELEMENT")

    assert sleeps == []
    assert not controller._pause_manager.is_paused()


@pytest.mark.parametrize("edited", [Element(name="button", x=5, y=1), None], ids=["save", "skip"])
def test_waits_the_delay_before_the_mouse_goes_back(controller, opened, fake_driver, monkeypatch, edited):
    opened.result = EditorResult(edited, ResumeMode.AFTER_5_S)
    moved_during_wait = []
    monkeypatch.setattr(
        "guimauve.controller.sleep_",
        lambda seconds: moved_during_wait.append((seconds, any(call[0] == "mouse_move" for call in fake_driver.calls))),
    )

    controller._trigger_editor(element(), "INVALID ELEMENT")

    assert moved_during_wait == [(5.0, False)]  # waited while suspended
    assert ("mouse_move",) == fake_driver.calls[-1][:1]  # the mouse goes back once the wait is over


def test_stays_paused_until_resumed(controller, opened, monkeypatch):
    opened.result = EditorResult(Element(name="button", x=5, y=1), ResumeMode.PAUSED)
    pause = controller._pause_manager
    seen = []

    def wait_while_paused():
        seen.append((pause.is_paused(), len(opened.persisted)))
        pause.resume()  # the pause shortcut

    monkeypatch.setattr(pause, "wait_while_paused", wait_while_paused)

    returned = controller._trigger_editor(element(), "INVALID ELEMENT")

    assert seen == [(True, 1)]  # paused once the element is saved
    assert returned is not None and not pause.is_paused()
