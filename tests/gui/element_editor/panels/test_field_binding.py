import pytest
from PySide6.QtWidgets import QComboBox, QSlider, QSpinBox

from guimauve.gui.element_editor_next.components import (
    AxisEditor,
    AxisMode,
    AxisPosition,
    ScreenEditor,
    SearchAreaEditor,
    TargetEditor,
)
from guimauve.gui.element_editor_next.panels import NO_EFFECT, ONE_SCREEN, FieldBinding, make_editor
from guimauve.gui.element_editor_next.schema import FIELDS
from guimauve.gui.element_editor_next.state import Mode, resolve


def values(store) -> dict:
    return {key: resolve(key, store.document, store.default).value for key in FIELDS}


@pytest.fixture
def bind(store, theme, qtbot):
    """Binding of a field to the store, shown once; every widget goes to qtbot, so none outlives the test."""

    def make(key: str, on=None) -> FieldBinding:
        binding = FieldBinding(on or store, FIELDS[key], theme)
        qtbot.addWidget(binding.field)
        binding.refresh(values(on or store))
        return binding

    return make


@pytest.mark.parametrize(
    ("key", "kind"),
    [("target", TargetEditor), ("search_area", SearchAreaEditor), ("screen", ScreenEditor), ("x", AxisEditor)],
)
def test_special_fields_have_their_editor(theme, qtbot, key, kind):
    editor = make_editor(FIELDS[key], theme)
    qtbot.addWidget(editor)
    assert isinstance(editor, kind)


def test_edit_sets_the_element(store, bind):
    binding = bind("timeout")

    binding.field.edited.emit(9)

    assert store.document.element.timeout == 9
    assert store.undo_label == "Timeout"


def test_reset_removes_the_own_value(make_store, bind):
    store = make_store(timeout=9)
    binding = bind("timeout", on=store)

    binding.field.reset_requested.emit()

    assert store.document.element.timeout is None


def test_in_test_mode_an_edit_is_a_trial(store, bind):
    binding = bind("timeout")
    store.set_mode(Mode.TEST)

    binding.field.edited.emit(9)

    assert store.document.trials.element == {"timeout": 9}
    assert store.document.element.timeout is None


def test_axis_sets_its_two_fields_in_one_step(make_store, bind):
    store = make_store(rel_x=10)
    binding = bind("x", on=store)

    binding.field.edited.emit(AxisPosition(AxisMode.ABSOLUTE, 1280))
    assert (store.document.element.x, store.document.element.rel_x) == (1280, None)

    store.undo()
    assert (store.document.element.x, store.document.element.rel_x) == (None, 10)


def test_axis_shows_its_two_fields_as_one(make_store, bind):
    store = make_store(rel_y=-10)
    binding = bind("y", on=store)

    state = binding.refresh(values(store))

    assert (state.value, state.own) == (AxisPosition(AxisMode.FROM_MOUSE, -10), True)


@pytest.mark.parametrize(("screen", "negative"), [(1, False), ([2, 1], False), (0, True)])
def test_axis_negative_only_from_the_primary_screen(make_store, bind, screen, negative):
    store = make_store(screen=screen, x=5)
    binding = bind("x", on=store)

    absolute = binding.field.editor.findChildren(QSpinBox)[0]
    assert (absolute.minimum() < 0) is negative


def test_slider_drag_is_one_step(store, bind):
    binding = bind("template_confidence_threshold")
    slider = binding.field.findChild(QSlider)

    slider.sliderPressed.emit()
    for value in (50, 60, 70):
        slider.setValue(value)
    slider.sliderReleased.emit()
    binding.field.edited.emit(0.5)

    store.undo()
    assert store.document.element.template_confidence_threshold == pytest.approx(0.7)
    store.undo()
    assert store.document.element.template_confidence_threshold is None


def test_code_value_is_shown_beside_the_label(store, bind):
    state = bind("mouse_speed").refresh(values(store))

    assert (state.value, state.code) == (0, 500)


def test_no_effect_with_a_fixed_position(make_store, bind):
    store = make_store(x=10)
    binding = bind("find_all", on=store)

    state = binding.refresh(values(store))

    assert state.disabled_reason == NO_EFFECT
    assert not binding.field.isEnabled()


def test_screen_disabled_without_screens(make_store, bind):
    store = make_store(screens=[])
    binding = bind("screen", on=store)

    assert binding.refresh(values(store)).disabled_reason == ONE_SCREEN


def test_target_offers_the_names_shared_by_the_image_variants(store, bind):
    combo = bind("target").field.findChild(QComboBox)

    assert [combo.itemText(index) for index in range(combo.count())] == ["Default", "", "icon"]


def test_hidden_by_its_rule(store, bind):
    binding = bind("feature_sigma")

    assert binding.field.isHidden()  # feature matching is off by default


def test_issues_of_an_axis_come_from_its_two_fields(make_store, bind):
    store = make_store(x=10, rel_x=5)
    binding = bind("x", on=store)

    assert binding.refresh(values(store)).error is not None
