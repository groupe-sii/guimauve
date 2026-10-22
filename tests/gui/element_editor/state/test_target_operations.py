import pytest

from guimauve.gui.element_editor_next.schema import override_groups
from guimauve.gui.element_editor_next.state import ELEMENT, Mode
from guimauve.models.variant import ImageVariant, TextVariant


def light(store) -> int:
    return store.variant_keys()[0]


def target(store, index: int) -> int:
    return store.document.key(store.document.variants[0].targets[index])


def test_rename_target(store):
    store.rename_target(light(store), target(store, 0), "logo")

    assert [t.name for t in store.document.variants[0].targets] == ["logo", "arrow"]
    assert store.undo_label == "Rename target"


def test_rename_the_default_target_updates_the_variant(store):
    store.set_field(light(store), "default_target", "icon")

    store.rename_target(light(store), target(store, 0), "logo")

    assert store.document.variants[0].default_target == "logo"
    store.undo()
    assert store.document.variants[0].default_target == "icon"


def test_remove_target_clears_the_default_target(store):
    store.set_field(light(store), "default_target", "icon")

    store.remove_target(light(store), target(store, 0))

    variant = store.document.variants[0]
    assert [t.name for t in variant.targets] == ["arrow"]
    assert variant.default_target is None
    assert store.undo_label == "Delete target"


def test_remove_another_target_keeps_the_default_target(store):
    store.set_field(light(store), "default_target", "icon")

    store.remove_target(light(store), target(store, 1))

    assert store.document.variants[0].default_target == "icon"


def test_override_copies_the_inherited_value(store):
    store.set_field(ELEMENT, "match_index", 3)

    store.override(light(store), "match_index", "Index")

    assert store.document.variants[0].match_index == 3
    assert store.undo_label == "Override Index"


def test_override_takes_the_code_value_when_it_applies(store):
    store.override(light(store), "mouse_speed")

    assert store.document.variants[0].mouse_speed == 500


def test_override_in_test_mode_is_a_trial(store):
    store.set_mode(Mode.TEST)

    store.override(light(store), "match_index")

    assert store.document.variants[0].match_index is None
    assert store.has_trials


@pytest.mark.parametrize("model", [ImageVariant, TextVariant])
def test_override_groups_never_offer_element_settings(model):
    keys = {field.key for _, fields in override_groups(model) for field in fields}

    assert not keys & {"timeout", "find_all", "screen", "target", "x", "y"}
    assert "search_area" in keys and "mouse_speed" in keys


def test_override_groups_by_detection_method():
    groups = dict(override_groups(ImageVariant))

    assert [f.key for f in groups["Image detection"]] == ["use_template", "use_feature", "use_ocr"]
    assert [f.key for f in groups["Template matching"]] == ["template_grayscale", "template_confidence_threshold"]
    assert "Text detection" not in groups


def test_override_groups_of_a_text_variant():
    assert [title for title, _ in override_groups(TextVariant)] == [
        "Where to search",
        "Text detection",
        "Multiple matches",
        "Mouse",
    ]
