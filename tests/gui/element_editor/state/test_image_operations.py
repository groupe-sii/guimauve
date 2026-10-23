import numpy as np
import pytest

from guimauve.gui.element_editor_next.state import Mode
from guimauve.gui.element_editor_next.state.commands import Group, SetValue
from guimauve.gui.element_editor_next.state.geometry import cropped_match_area, match_area, outside
from guimauve.models.area import Area
from guimauve.models.variant import ImageVariant, Target


def area(left: int, top: int, right: int, bottom: int) -> Area:
    return Area(left=left, top=top, right=right, bottom=bottom)


def light(store) -> int:
    return store.variant_keys()[0]


def variant(store):
    return store.document.variants[0]


def target(store, index: int) -> int:
    return store.document.key(variant(store).targets[index])


def numbered(height: int = 40, width: int = 120) -> np.ndarray:
    """Image whose pixels tell where they come from: red is the column, green the row."""
    image = np.zeros((height, width, 3), np.uint8)
    image[..., 0] = np.arange(width)[None, :]
    image[..., 1] = np.arange(height)[:, None]
    return image


# Geometry


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (None, None),
        (area(0, 0, 120, 40), None),  # the whole image
        (area(0, 0, 200, 90), None),  # beyond the whole image
        (area(10, 5, 50, 30), area(10, 5, 50, 30)),
        (area(100, 10, 200, 30), area(100, 10, 120, 30)),  # clipped to the image
        (area(130, 0, 200, 30), None),  # nothing left
    ],
)
def test_match_area_is_kept_inside_the_image(given, expected):
    assert match_area(given, 120, 40) == expected


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (None, None),
        (area(20, 10, 40, 20), area(10, 5, 30, 15)),  # moved with the crop
        (area(0, 0, 40, 20), area(0, 0, 30, 15)),  # clipped to the crop
        (area(0, 0, 10, 5), None),  # outside the crop
        (area(0, 0, 120, 40), None),  # covers the whole crop
    ],
)
def test_cropped_match_area(given, expected):
    assert cropped_match_area(given, area(10, 5, 100, 35)) == expected


def test_outside_lists_the_targets_outside_an_area():
    inside, on_right_edge, above = Target(x=10, y=10), Target(x=50, y=10), Target(x=10, y=2)

    assert outside([inside, on_right_edge, above], area(0, 5, 50, 20)) == [on_right_edge, above]
    assert outside(None, area(0, 5, 50, 20)) == []


# Group gesture


def test_groups_of_one_gesture_merge(store):
    key = target(store, 0)
    first = Group([SetValue(key, "x", 1, gesture=7), SetValue(key, "y", 2, gesture=7)], gesture=7)
    second = Group([SetValue(key, "x", 3, gesture=7), SetValue(key, "y", 4, gesture=7)], gesture=7)

    assert first.merge(second)
    assert [command.value for command in first.commands] == [3, 4]


def test_groups_changing_other_fields_stay_apart(store):
    first = Group([SetValue(target(store, 0), "x", 1, gesture=7)], gesture=7)

    assert not first.merge(Group([SetValue(target(store, 1), "x", 3, gesture=7)], gesture=7))
    assert not first.merge(Group([SetValue(target(store, 0), "x", 3, gesture=8)], gesture=8))
    assert not Group([SetValue(target(store, 0), "x", 1)]).merge(Group([SetValue(target(store, 0), "x", 3)]))


# Targets


def test_add_target_selects_it(store):
    added = store.add_target(light(store), 30, 15)

    new = variant(store).targets[-1]
    assert (new.name, new.x, new.y) == (None, 30, 15)
    assert (store.selected_variant, store.selected_target) == (light(store), added)
    assert store.undo_label == "Add target"


def test_add_target_to_a_variant_without_targets(make_store):
    store = make_store([ImageVariant(name="plain", image=numbered())])

    store.add_target(light(store), 5, 5)

    assert len(variant(store).targets) == 1
    store.undo()
    assert variant(store).targets is None


def test_add_target_outside_the_image_is_reported(store):
    added = store.add_target(light(store), -5, 50)

    new = variant(store).targets[-1]
    assert (new.x, new.y) == (-5, 50)
    assert {issue.code for issue in store.issues_of(added)} == {"target_outside"}


def test_move_target(store):
    store.move_target(target(store, 0), 50, 30)

    assert (variant(store).targets[0].x, variant(store).targets[0].y) == (50, 30)
    assert store.undo_label == "Move target"
    store.undo()
    assert (variant(store).targets[0].x, variant(store).targets[0].y) == (10, 20)


def test_moves_of_one_drag_are_undone_at_once(store):
    gesture = store.new_gesture()
    for x in (20, 30, 40):
        store.move_target(target(store, 0), x, x // 2, gesture)

    store.undo()

    assert (variant(store).targets[0].x, variant(store).targets[0].y) == (10, 20)
    assert not store.can_undo


def test_move_target_outside_the_image(store):
    store.move_target(target(store, 0), 200, -10)

    assert (variant(store).targets[0].x, variant(store).targets[0].y) == (200, -10)
    assert {issue.code for issue in store.issues_of(target(store, 0))} == {"target_outside"}


def test_move_target_in_place_does_nothing(store):
    store.move_target(target(store, 0), 10, 20)

    assert not store.can_undo


def test_nudge_target(store):
    store.nudge_target(target(store, 0), 10, -1)
    store.nudge_target(target(store, 0), 1, 0)

    assert (variant(store).targets[0].x, variant(store).targets[0].y) == (21, 19)
    store.undo()
    assert variant(store).targets[0].x == 20  # one undo step per nudge


def test_target_moves_are_never_trials(store):
    store.set_mode(Mode.TEST)

    store.move_target(target(store, 0), 50, 30)

    assert variant(store).targets[0].x == 50
    assert not store.has_trials


# Match area


def test_set_match_area(store):
    store.set_match_area(light(store), area(10, 5, 60, 30))

    assert variant(store).match_area == area(10, 5, 60, 30)
    assert store.undo_label == "Match area"


def test_match_area_of_the_whole_image_is_none(store):
    store.set_match_area(light(store), area(10, 5, 60, 30))

    store.set_match_area(light(store), area(0, 0, 120, 40))

    assert variant(store).match_area is None


def test_same_match_area_does_nothing(store):
    store.set_match_area(light(store), area(0, 0, 500, 500))

    assert not store.can_undo


# Recapture


def test_replace_image_keeps_the_targets_and_resets_the_match_area(store):
    store.set_match_area(light(store), area(10, 5, 60, 30))
    image = np.zeros((10, 15, 3), np.uint8)

    store.replace_image(light(store), image)

    assert variant(store).image is image
    assert variant(store).match_area is None
    assert [t.name for t in variant(store).targets] == ["icon", "arrow"]
    assert store.undo_label == "Replace image"


def test_targets_outside_a_new_image_are_reported(store):
    store.replace_image(light(store), np.zeros((10, 15, 3), np.uint8))  # targets at x 10, y 20

    assert {issue.code for issue in store.issues_of(target(store, 0))} == {"target_outside"}


def test_undo_replace_image(store):
    before = variant(store).image
    store.set_match_area(light(store), area(10, 5, 60, 30))

    store.replace_image(light(store), np.zeros((10, 15, 3), np.uint8))
    store.undo()

    assert variant(store).image is before
    assert variant(store).match_area == area(10, 5, 60, 30)


# Crop


def test_crop_cuts_the_image(store):
    store.replace_image(light(store), numbered())

    assert store.crop(light(store), area(5, 10, 65, 35))

    image = variant(store).image
    assert image.shape == (25, 60, 3)
    assert tuple(image[0, 0, :2]) == (5, 10)
    assert store.undo_label == "Crop image"


def test_crop_moves_the_targets_and_keeps_those_left_outside(store):
    store.move_target(target(store, 1), 100, 30)
    store.set_field(light(store), "default_target", "arrow")

    store.crop(light(store), area(5, 10, 65, 35))

    targets = variant(store).targets
    assert [(t.name, t.x, t.y) for t in targets] == [("icon", 5, 10), ("arrow", 95, 20)]
    assert variant(store).default_target == "arrow"
    assert [issue.code for issue in store.issues_of(target(store, 1))] == ["target_outside"]
    assert store.issues_of(target(store, 0)) == []


def test_crop_clips_the_match_area(store):
    store.set_match_area(light(store), area(0, 0, 40, 20))

    store.crop(light(store), area(10, 5, 100, 35))

    assert variant(store).match_area == area(0, 0, 30, 15)


def test_undo_crop(store):
    image = variant(store).image
    store.set_match_area(light(store), area(0, 0, 40, 20))
    store.set_field(light(store), "default_target", "arrow")
    store.move_target(target(store, 1), 100, 30)
    keys = [target(store, 0), target(store, 1)]

    store.crop(light(store), area(5, 10, 65, 35))
    store.undo()

    restored = variant(store)
    assert restored.image is image
    assert [(t.x, t.y) for t in restored.targets] == [(10, 20), (100, 30)]
    assert [store.document.key(t) for t in restored.targets] == keys
    assert restored.default_target == "arrow"
    assert restored.match_area == area(0, 0, 40, 20)


@pytest.mark.parametrize("crop", [area(0, 0, 120, 40), area(0, 0, 300, 300), area(130, 0, 200, 40)])
def test_crop_of_nothing_is_refused(store, crop):
    assert not store.crop(light(store), crop)
    assert not store.can_undo


def test_crop_beyond_the_image_is_clipped(store):
    assert store.crop(light(store), area(60, 0, 300, 300))

    assert variant(store).image.shape[:2] == (40, 60)
