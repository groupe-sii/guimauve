from types import SimpleNamespace

import pytest

from guimauve.models.element import Element
from guimauve.models.model import ModelError
from guimauve.models.variant import ImageVariant

ROOT_ACTION_LEAK = "handle_action does not reset _root_action when the action stops early"


@pytest.fixture
def missing(needle_path, detectors):
    """Image element that the fake detectors never find."""
    return Element(name="missing", timeout=0.05, variants=[ImageVariant(name="variant", path=needle_path)])


@pytest.fixture
def editor(monkeypatch, make_controller):
    """Controller in debug mode whose element editor is a recorder returning `editor.result`."""
    editor = SimpleNamespace(controller=make_controller(parameters={"debug_elements": True}), calls=[], result=None)

    def fake_trigger_editor(element, message):
        editor.calls.append((element.name, message, editor.controller._root_action))
        return editor.result

    monkeypatch.setattr(editor.controller, "_trigger_editor", fake_trigger_editor)
    return editor


def aliased(element: Element) -> Element:
    element._alias = "app"
    return element


def test_undefined_element_raises(controller, inputs):
    element = Element(name="new", x=1, y=1)
    element._is_new = True
    with pytest.raises(Exception, match="Element new is not defined"):
        controller.click(on=element)
    assert inputs() == []


def test_invalid_element_raises_model_error(controller, inputs):
    with pytest.raises(ModelError):
        controller.click(on=Element(name="invalid", x=1, rel_x=2))
    assert inputs() == []


def test_element_not_on_screen_raises(controller, inputs, missing):
    with pytest.raises(Exception, match="Element missing not found on screen"):
        controller.click(on=missing)
    assert inputs() == []


def test_editor_needs_debug_elements(controller, monkeypatch, missing):
    monkeypatch.setattr(controller, "_trigger_editor", pytest.fail)
    with pytest.raises(Exception, match="not found on screen"):
        controller.click(on=aliased(missing))


def test_editor_needs_an_alias(editor, missing):
    with pytest.raises(Exception, match="not found on screen"):
        editor.controller.click(on=missing)
    assert editor.calls == []


def test_editor_receives_problem_and_root_action(editor, missing):
    editor.controller.double_click(on=aliased(missing))
    assert editor.calls == [("missing", "ELEMENT NOT FOUND ON SCREEN", "double_click")]


def test_cancelled_edition_skips_action(editor, inputs, missing):
    assert editor.controller.click(on=aliased(missing)) is None
    assert inputs() == []


def test_edited_element_is_used(editor, inputs, missing):
    editor.result = Element(name="missing", x=10, y=20)
    editor.controller.click(on=aliased(missing))
    assert inputs()[0] == ("mouse_move", 10, 20)


def test_root_action_is_reset_after_action(controller):
    controller.click(on=Element(name="point", x=1, y=1))
    assert controller._root_action is None


def test_root_action_is_reset_after_failure(controller, missing):
    with pytest.raises(Exception):
        controller.click(on=missing)
    assert controller._root_action is None


def test_root_action_is_reset_after_cancelled_edition(editor, missing):
    editor.controller.click(on=aliased(missing))
    assert editor.controller._root_action is None
