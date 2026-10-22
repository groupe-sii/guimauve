import numpy as np
import pytest

from guimauve.gui.element_editor_next.state import ELEMENT, Mode, copy_name, new_name, normalize_name
from guimauve.models.variant import ImageVariant, Target, TextVariant


def names(store) -> list[str]:
    return [variant.name for variant in store.document.variants]


def key(store, index: int) -> int:
    return store.variant_keys()[index]


@pytest.mark.parametrize(
    ("taken", "expected"),
    [([], "VARIANT_1"), (["VARIANT_1", "VARIANT_3"], "VARIANT_2"), (["LIGHT"], "VARIANT_1")],
)
def test_new_name_takes_the_first_free_number(taken, expected):
    assert new_name(taken) == expected


@pytest.mark.parametrize(
    ("taken", "expected"),
    [
        (["LIGHT"], "LIGHT_COPY"),
        (["LIGHT", "LIGHT_COPY"], "LIGHT_COPY_2"),
        (["LIGHT_COPY", "LIGHT_COPY_2"], "LIGHT_COPY_3"),
    ],
)
def test_copy_name(taken, expected):
    assert copy_name("LIGHT", taken) == expected


def test_add_variant_at_the_end_and_select_it(store):
    variant = TextVariant(name="label", text="Sign in")

    added = store.add_variant(variant)

    assert names(store) == ["light", "dark", "label"]
    assert store.selected_variant == added == store.document.key(variant)
    assert store.undo_label == "Add variant"


def test_undo_add_moves_the_selection_back(store):
    store.add_variant(TextVariant(name="label", text="Sign in"))

    store.undo()

    assert names(store) == ["light", "dark"]
    assert store.selected_variant == key(store, 1)


def test_duplicate_inserts_a_deep_copy_after_the_source(store):
    source = store.document.variants[0]

    copy_key = store.duplicate_variant(key(store, 0))

    copy = store.document.get(copy_key)
    assert names(store) == ["light", "LIGHT_COPY", "dark"]
    assert store.selected_variant == copy_key
    assert copy.image is not source.image and np.array_equal(copy.image, source.image)
    assert [t.name for t in copy.targets] == ["icon", "arrow"]
    assert copy.targets[0] is not source.targets[0]
    assert store.document.key(copy.targets[0]) != store.document.key(source.targets[0])


def test_duplicate_twice_finds_a_free_name(store):
    store.duplicate_variant(key(store, 0))
    store.duplicate_variant(key(store, 0))

    assert names(store) == ["light", "LIGHT_COPY_2", "LIGHT_COPY", "dark"]


def test_remove_variant_selects_the_nearest(store):
    store.remove_variant(key(store, 0))

    assert names(store) == ["dark"]
    assert store.selected_variant == key(store, 0)
    assert store.undo_label == "Delete variant"


def test_move_variant(store):
    dark = key(store, 1)

    store.move_variant(dark, 0)

    assert names(store) == ["dark", "light"]
    assert store.undo_label == "Move variant"


@pytest.mark.parametrize("index", [-1, 1, 2])
def test_move_out_of_the_list_or_in_place_does_nothing(store, index):
    store.move_variant(key(store, 1), index)

    assert names(store) == ["light", "dark"]
    assert not store.can_undo


@pytest.mark.parametrize(
    ("name", "expected"), [("default", "DEFAULT"), ("  dark theme ", "DARK_THEME"), ("A  b", "A_B")]
)
def test_normalize_name(name, expected):
    assert normalize_name(name) == expected


def test_rename_variant_even_in_test_mode(store):
    store.set_mode(Mode.TEST)

    assert store.rename_variant(key(store, 0), "default")

    assert names(store) == ["DEFAULT", "dark"]
    assert not store.has_trials
    assert store.undo_label == "Rename variant"


@pytest.mark.parametrize("name", ["", "  ", "Dark", "DARK"])
def test_rename_refuses_an_empty_or_taken_name(make_store, name):
    store = make_store([TextVariant(name="LIGHT", text="a"), TextVariant(name="DARK", text="b")])

    assert not store.rename_variant(key(store, 0), name)

    assert names(store) == ["LIGHT", "DARK"]
    assert not store.can_undo


def test_rename_to_the_same_name_does_nothing(make_store):
    store = make_store([TextVariant(name="LIGHT", text="a")])

    assert store.rename_variant(key(store, 0), "light")

    assert not store.can_undo


def test_summary_counts_the_overrides_and_trials(store):
    light = key(store, 0)
    store.set_field(light, "mouse_speed", 100)
    store.set_mode(Mode.TEST)
    store.set_field(light, "match_index", 2)
    store.set_field(ELEMENT, "timeout", 3)  # an element value is not an override

    assert store.variant_summary(light).overrides == 2
    assert store.variant_summary(key(store, 1)).overrides == 0


def test_summary_includes_the_issues_of_the_targets(make_store):
    outside = ImageVariant(
        name="light", image=np.zeros((10, 10, 3), np.uint8), targets=[Target(name="far", x=50, y=50)]
    )
    store = make_store([outside, ImageVariant(name="empty")])

    assert store.variant_summary(key(store, 0)).warnings == ("Target outside the image",)
    assert store.variant_summary(key(store, 1)).errors == ("No image",)


def test_summary_of_a_duplicate_name(make_store):
    store = make_store([TextVariant(name="label", text="a"), TextVariant(name="label", text="b")])

    assert all(store.variant_summary(k).errors for k in store.variant_keys())
