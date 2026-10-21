import pytest

from guimauve.gui.element_editor_next.components import (
    NOT_SET,
    AxisMode,
    AxisPosition,
    axis_position,
    axis_resolution,
    axis_values,
)
from guimauve.gui.element_editor_next.state import Resolution, Source


@pytest.mark.parametrize(
    ("absolute", "relative", "position"),
    [
        (None, None, NOT_SET),
        (1280, None, AxisPosition(AxisMode.ABSOLUTE, 1280)),
        (None, -10, AxisPosition(AxisMode.FROM_MOUSE, -10)),
        (1280, 10, AxisPosition(AxisMode.ABSOLUTE, 1280)),  # a conflict: the absolute value wins, as at run time
    ],
)
def test_position_from_the_two_fields(absolute, relative, position):
    assert axis_position(absolute, relative) == position


@pytest.mark.parametrize(
    ("position", "values"),
    [
        (None, (None, None)),
        (NOT_SET, (None, None)),
        (AxisPosition(AxisMode.ABSOLUTE, 0), (0, None)),
        (AxisPosition(AxisMode.FROM_MOUSE, -10), (None, -10)),
    ],
)
def test_values_of_the_two_fields(position, values):
    assert axis_values(position) == values


@pytest.mark.parametrize(
    ("position", "label"),
    [
        (NOT_SET, "not set"),
        (AxisPosition(AxisMode.ABSOLUTE, 1280), "1280"),
        (AxisPosition(AxisMode.FROM_MOUSE, 10), "mouse + 10"),
        (AxisPosition(AxisMode.FROM_MOUSE, -10), "mouse − 10"),
    ],
)
def test_label(position, label):
    assert position.label == label


def test_resolution_merges_the_layers_of_the_two_fields():
    absolute = Resolution(1280, Source.ELEMENT, {Source.ELEMENT: 1280})
    relative = Resolution(10, Source.CODE, {Source.CODE: 10})

    merged = axis_resolution(absolute, relative)

    assert merged.layers == {
        Source.ELEMENT: AxisPosition(AxisMode.ABSOLUTE, 1280),
        Source.CODE: AxisPosition(AxisMode.FROM_MOUSE, 10),
    }
    assert (merged.value, merged.source) == (AxisPosition(AxisMode.FROM_MOUSE, 10), Source.CODE)


def test_resolution_of_an_axis_not_set():
    undefined = Resolution(None, None, {})

    assert axis_resolution(undefined, undefined) == undefined
